import argparse
import csv
import datetime
import html
import json
import os
import re
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# Implement some rudimentary caching to prevent the SBOE from hating me.
def get_data_file(election_date, filename, url, update=False):
    data_dir = os.path.join('data', election_date)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    file_path = os.path.join(data_dir, filename)

    download_data = False
    if not os.path.exists(file_path):
        download_data = True
    else:
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if datetime.now() - file_mod_time > timedelta(hours=1):
            download_data = True
    if update:
        download_data = True

    if download_data:
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            data_timestamp = datetime.now()
        except requests.exceptions.RequestException as e:
            print(f'Error fetching data from URL: {e}')
            return None, None
    else:
        data_timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON data from {filename}: {e}')
        return None, None

    return data, data_timestamp

# Make the report look a bit nicer
# (i.e., instead of NC STATE HOUSE OF REP..., NC State House of Representatives)
def contest_title_format(text):
    words = text.split()
    exceptions = {'nc': 'NC', 'of': 'of', 'us': 'US'}
    return ' '.join(
        exceptions.get(word.lower(), word.title())
        for word in words
    )

def main():
    parser = argparse.ArgumentParser(description='Process election data and generate a report.')
    parser.add_argument('--output', '-o', type=str, default='results', help='Path to the output file')
    parser.add_argument('--election', '-e', type=str, help='Election date in YYYYMMDD format')
    parser.add_argument('--contests', type=str, help='Comma-separated list of contest types to include')
    parser.add_argument('--limit', '-l', type=int, default=100, help='Limit the number of contests displayed')
    parser.add_argument('--margin', type=float, help='Only include contests with a margin less than or equal to this number')
    parser.add_argument('--method', type=str, choices=['percentage', 'votes'], default='percentage', help="Method to determine closest contests: 'percentage' or 'votes'")
    parser.add_argument('--format', type=str, choices=['html', 'csv'], default='html', help="Output format: 'html' or 'csv'")
    parser.add_argument('--counties', '-c', type=str, help="Comma-separated list of county names (default is statewide)")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to include additional debug information')
    parser.add_argument('--update', action='store_true', help='Force update of cached data')
    args = parser.parse_args()

    # Ensure the output file has the correct extension
    if not args.output.endswith(f'.{args.format}'):
        args.output += f'.{args.format}'

    # Determine the election date
    if args.election:
        election_date = args.election
    else:
        elections_url = 'https://er.ncsbe.gov/enr/elections.txt'
        elections_data, data_timestamp = get_data_file('latest', 'elections.txt', elections_url, update=args.update)
        if elections_data is None:
            return
        if not elections_data:
            print('No elections found.')
            return
        edt = elections_data[0]['edt']
        election_date = datetime.strptime(edt, '%m/%d/%Y').strftime('%Y%m%d')

    # Fetch county information
    county_url = f'https://er.ncsbe.gov/enr/{election_date}/data/county.txt'
    counties_data, data_timestamp = get_data_file(election_date, 'county.txt', county_url, update=args.update)
    if counties_data is None:
        if args.election:
            print("There doesn't appear to be an election on that date.")
        else:
            print('Error fetching county data.')
        return

    county_name_to_id = {county['cnm'].upper(): county['cid'] for county in counties_data}

    if args.counties:
        county_names_list = [c.strip().upper() for c in args.counties.split(',')]
        county_ids = []
        county_names = []
        not_found_counties = []
        for name in county_names_list:
            if name.upper() in county_name_to_id:
                county_ids.append(county_name_to_id[name.upper()])
                county_names.append(name.title())
            else:
                not_found_counties.append(name.title())
        if not_found_counties:
            print(f"Counties not found: {', '.join(not_found_counties)}")
            return
        filters_applied = [f'Only showing results for counties: {", ".join(county_names)}']
    else:
        county_ids = ['0']
        filters_applied = []

    office_url = f'https://er.ncsbe.gov/enr/{election_date}/data/office.txt'
    office_data, office_timestamp = get_data_file(election_date, 'office.txt', office_url, update=args.update)
    if office_data is None:
        print('Error fetching office data.')
        return

    data_timestamp = max(data_timestamp, office_timestamp)

    contest_types_friendly = {item['lbl']: item['des'].title() for item in office_data}
    valid_contest_codes = set(contest_types_friendly.keys())

    if args.contests:
        contest_types_list = [c.strip().upper() for c in args.contests.split(',')]
        invalid_contests = [c for c in contest_types_list if c not in valid_contest_codes]
        if invalid_contests:
            print(f"Invalid contest codes: {', '.join(invalid_contests)}")
            print(f"Valid contest codes are: {', '.join(valid_contest_codes)}")
            return
        friendly_contest_names = [contest_title_format(contest_types_friendly.get(c, c)) for c in contest_types_list]
        filters_applied.append(f'Contests of type: {", ".join(friendly_contest_names)}')
        contest_types = set(contest_types_list)
    else:
        contest_types = None

    if args.margin is not None:
        if args.method == 'percentage':
            filters_applied.append(f'Margin between top two candidates is less than or equal to {args.margin}%')
        else:
            filters_applied.append(f'Margin between top two candidates is less than or equal to {int(args.margin):,} votes')

    if args.limit is not None:
        filters_applied.append(f'Limiting number of contests displayed to {args.limit}')

    filters_applied.append(f'Method used to determine closest contests: {args.method.capitalize()}')

    contests = defaultdict(list)

    for county_id in county_ids:
        data_filename = f'results_{county_id}.txt'
        data_url = f'https://er.ncsbe.gov/enr/{election_date}/data/{data_filename}'
        data, results_timestamp = get_data_file(election_date, data_filename, data_url, update=args.update)
        if data is None:
            print('Error fetching results data.')
            return

        data_timestamp = max(data_timestamp, results_timestamp)

        for entry in data:
            contest_type = entry.get('ogl', '').upper()
            if contest_types and contest_type not in contest_types:
                continue

            contest_name = entry['cnm']
            # Remove '(VOTE FOR X)' from contest names for readability
            contest_name = re.sub(r'\s*\(VOTE FOR \d+\)', '', contest_name, flags=re.IGNORECASE)

            contest_key = (contest_name, entry.get('cid', county_id))
            contests[contest_key].append(entry)

    contest_results = []

    for (contest_name, contest_county_id), candidates in contests.items():
        for candidate in candidates:
            candidate['vct'] = int(candidate['vct'])
            candidate['pct'] = float(candidate['pct'])
        sorted_candidates = sorted(candidates, key=lambda x: x['vct'], reverse=True)
        total_votes = sum(c['vct'] for c in sorted_candidates)
        if len(sorted_candidates) >= 2:
            top_candidate = sorted_candidates[0]
            second_candidate = sorted_candidates[1]
            vote_margin = top_candidate['vct'] - second_candidate['vct']
            percentage_margin = top_candidate['pct'] - second_candidate['pct']
        else:
            top_candidate = sorted_candidates[0]
            second_candidate = None
            vote_margin = top_candidate['vct']
            percentage_margin = None
        if args.margin is not None:
            if percentage_margin is None:
                continue
            if args.method == 'percentage':
                if (percentage_margin * 100) > args.margin:
                    continue
            else:
                if vote_margin > args.margin:
                    continue
        contest_county_name = next((name.title() for name, cid in county_name_to_id.items() if cid == contest_county_id), 'Statewide')
        contest_results.append({
            'contest_name': f"{contest_name} ({contest_county_name})",
            'contest_type_code': candidates[0]['ogl'],  # Store contest type code
            'candidates': sorted_candidates,
            'top_candidate': top_candidate,
            'second_candidate': second_candidate,
            'vote_margin': vote_margin,
            'percentage_margin': percentage_margin,
            'total_votes': total_votes,
            'debug_data': candidates if args.debug else None
        })

    if args.method == 'percentage':
        contest_results_sorted = sorted(
            contest_results,
            key=lambda x: (x['percentage_margin'] is None, x['percentage_margin'])
        )
    else:
        contest_results_sorted = sorted(
            contest_results,
            key=lambda x: (x['vote_margin'] is None, x['vote_margin'])
        )

    if args.limit is not None:
        contest_results_sorted = contest_results_sorted[:args.limit]

    data_timestamp_str = data_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    print(f"Using data that was last updated on: {data_timestamp_str}")

    # Count the number of contests per contest type
    contest_type_counts = defaultdict(int)
    for contest in contest_results_sorted:
        contest_type_code = contest['contest_type_code']
        contest_type_counts[contest_type_code] += 1

    # Prepare friendly names and sort counts
    contest_type_counts_friendly = []
    for code, count in contest_type_counts.items():
        friendly_name = contest_types_friendly.get(code, code)
        friendly_name_formatted = contest_title_format(friendly_name)
        contest_type_counts_friendly.append((friendly_name_formatted, count))
    contest_type_counts_friendly.sort(key=lambda x: x[0])  # Sort alphabetically

    if args.format == 'html':
        html_content = f'''
    <html>
    <head>
        <title>Election Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .contest {{ margin-bottom: 30px; }}
            .contest h2 {{ margin-bottom: 10px; }}
            .candidates {{ margin-left: 20px; }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-top: 10px;
                table-layout: fixed;
            }}
            th, td {{
                text-align: left;
                padding: 8px;
                border: 1px solid #ddd;
                width: 25%;
                word-wrap: break-word;
            }}
            tr:nth-child(even){{background-color: #f2f2f2}}
            th {{ background-color: #172c4a; color: white; }}
            tfoot td {{ font-weight: bold; }}
            .filters {{ margin-bottom: 20px; }}
            .filters h3 {{ margin-bottom: 5px; }}
            .filters ul {{ list-style-type: disc; margin-left: 20px; }}
            /* Summary table styles */
            .summary-table table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            .summary-table th, .summary-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            .summary-table th {{
                background-color: #172c4a;
                color: white;
            }}
            /* Debug styles */
            .debug-toggle {{
                margin-top: 10px;
            }}
            .debug-content {{
                display: none;
                background-color: #f9f9f9;
                padding: 10px;
                border: 1px solid #ccc;
                white-space: pre-wrap;
                font-family: monospace;
            }}
        </style>
        <script>
            function toggleDebug(id) {{
                var content = document.getElementById(id);
                if (content.style.display === "none") {{
                    content.style.display = "block";
                }} else {{
                    content.style.display = "none";
                }}
            }}
        </script>
    </head>
    <body>
        <h2>Closest Election Results for the {datetime.strptime(election_date, "%Y%m%d").strftime("%m-%d-%Y")} Election</h2>
        <p>Data last updated on: {datetime.strptime(data_timestamp_str, "%Y-%m-%d %H:%M:%S").strftime("%m-%d-%Y at %H:%M:%S")}</p>
    '''

        if filters_applied:
            html_content += '    <div class="filters">\n'
            html_content += '      <h3>Report generated for contests where:</h3>\n'
            html_content += '      <ul>\n'
            for filter_text in filters_applied:
                html_content += f'        <li>{filter_text}</li>\n'
            html_content += '      </ul>\n'
            html_content += '    </div>\n'

        # Include the summary table if more than one contest is gathered
        if len(contest_results_sorted) > 1:
            html_content += '    <div class="summary-table">\n'
            html_content += '      <h3>Number of Contests by Type:</h3>\n'
            html_content += '      <table>\n'
            # Headers
            html_content += '        <tr>\n'
            for friendly_name, _ in contest_type_counts_friendly:
                html_content += f'          <th>{friendly_name}</th>\n'
            html_content += '        </tr>\n'
            # Counts
            html_content += '        <tr>\n'
            for _, count in contest_type_counts_friendly:
                html_content += f'          <td>{count}</td>\n'
            html_content += '        </tr>\n'
            html_content += '      </table>\n'
            html_content += '    </div>\n'

        for idx, contest in enumerate(contest_results_sorted):
            contest_name = contest['contest_name']
            percentage_margin = contest['percentage_margin']
            vote_margin = contest['vote_margin']
            total_votes = contest['total_votes']
            html_content += f'<div class="contest">\n'
            html_content += f'  <h2>{contest_title_format(contest_name)}</h2>\n'
            if percentage_margin is not None:
                html_content += '  <p>Margin between top two candidates: '
                if args.method == 'percentage':
                    html_content += f'{percentage_margin*100:.2f}% ({vote_margin:,} votes)</p>\n'
                else:
                    html_content += f'{vote_margin:,} votes ({percentage_margin*100:.2f}%)</p>\n'
            else:
                html_content += f'  <p>Uncontested contest</p>\n'
            html_content += '  <div class="candidates">\n'
            html_content += '    <table>\n'
            html_content += '      <thead>\n'
            html_content += '        <tr><th>Candidate</th><th>Party</th><th>Votes</th><th>Percentage</th></tr>\n'
            html_content += '      </thead>\n'
            html_content += '      <tbody>\n'
            for candidate in contest['candidates']:
                bnm = candidate['bnm']
                pty = candidate['pty']
                vct = candidate['vct']
                pct = candidate['pct']
                html_content += f'        <tr><td>{bnm}</td><td>{pty}</td><td>{vct:,}</td><td>{pct*100:.2f}%</td></tr>\n'
            html_content += '      </tbody>\n'
            html_content += '      <tfoot>\n'
            html_content += f'        <tr><td colspan="2" style="background-color: #9fbae1;"><strong>Total</strong></td><td><strong>{total_votes:,}</strong></td><td><strong>100%</strong></td></tr>\n'
            html_content += '      </tfoot>\n'
            html_content += '    </table>\n'
            html_content += '  </div>\n'
            if args.debug:
                debug_data_json = json.dumps(contest['debug_data'], indent=2)
                debug_data_html = html.escape(debug_data_json)
                debug_content_id = f"debug-content-{idx}"
                html_content += f'''
                <div class="debug-toggle">
                    <button onclick="toggleDebug('{debug_content_id}')">Toggle Debug Info</button>
                </div>
                <div id="{debug_content_id}" class="debug-content">
                    <pre>{debug_data_html}</pre>
                </div>
                '''
            html_content += '</div>\n'

        html_content += '''
    </body>
    </html>
    '''

        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f'HTML report generated: {args.output}')
    elif args.format == 'csv':
        csv_headers = [
            'contest',
            'total_votes',
            'pct_margin_between_top_two',
            'vote_margin_between_top_two',
        ]

        for i in range(1, 6):
            csv_headers.extend([
                f'candidate_{i}',
                f'candidate_{i}_party',
                f'candidate_{i}_votes',
                f'candidate_{i}_pct'
            ])

        csv_headers.extend(['other_votes', 'other_vote_pct'])

        with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvfile.write(f'# Data last updated on: {data_timestamp_str}\n')
            csvwriter.writerow(csv_headers)
            for contest in contest_results_sorted:
                contest_name = contest['contest_name']
                total_votes = contest['total_votes']
                percentage_margin = contest['percentage_margin']
                vote_margin = contest['vote_margin']
                row = [
                    contest_name,
                    total_votes,
                    f"{percentage_margin*100:.2f}%" if percentage_margin is not None else '',
                    vote_margin,
                ]
                candidates = contest['candidates']
                for i in range(5):
                    if i < len(candidates):
                        c = candidates[i]
                        row.extend([
                            c['bnm'],
                            c['pty'],
                            c['vct'],
                            f"{c['pct']*100:.2f}%"
                        ])
                    else:
                        row.extend(['', '', '', ''])
                if len(candidates) > 5:
                    other_votes = sum(c['vct'] for c in candidates[5:])
                    other_vote_pct = sum(c['pct'] for c in candidates[5:]) * 100
                    row.extend([other_votes, f"{other_vote_pct:.2f}%"])
                else:
                    row.extend(['', ''])
                csvwriter.writerow(row)
        print(f'CSV report generated: {args.output}')

    else:
        print('Invalid format specified.')

if __name__ == '__main__':
    main()
