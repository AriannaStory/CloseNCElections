# NC Closest Election Results
A simple Python 3.x app to show the closest races in North Carolina elections.

![image](https://github.com/user-attachments/assets/c9ed10c1-462c-42d0-b0b0-b54469dafb7f)

## Installation
1. Clone this repository.
2. Install the Python requirements (`pip install -r requirements.txt`)


## Usage
To run this script, run the following from the command line:
`python election_results.py [options]`

Please note that, when you first get information about an election, it is cached locally for up to an hour. You can use the `--update` option to forcibly connect to the State Board of Elections and get new data.

### Options
* `--output` (or `-o`)<br>
The location to generate the report.<br>
Default: `output.html`

* `--election` (or `-e`)<br>
The date of the election you're interested in (in YYYYMMDD format).<br>Default: the most recent election.

* `--contest`<br>
A comma-separated list of election contests:<br>
Accepts:
  * **FED**: Federal (President, Senate, US House)
  * **COS**: Council of State (Governor, Attorney General, etc.)
  * **NCH**: NC House of Representatives
  * **NCS**: NC Senate
  * **JUD**: Judicial
  * **REF**: Referenda
  * **CCL**: Cross-County Local
  * **LOC**: Local

<!-- This is dumb. -->
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Default: All races

* `--limit` (or `-l`)<br>
The number of matching races to show, in descending order.<br>Default: `100`

* `--margin`<br>
Only show races with margins less than or equal to this number.

* `--method`<br>
Whether we should determine the closest races by votes or percentage.<br>
Accepts: `votes` or `percentage`<br>
Default: `percentage`

* `--format`<br>
The format that you want to receive the report in.<br>
Accepts: `html` or `csv`<br>
Default: `html`

* `--counties` (or `-c`)<br>
A comma-separated list of county names that we return data for.<br>
Accepts: A comma-separated list of NC county names<br>
Default: `0` (statewide)

* `--debug`<br>
Shows the actual data that was used in generating the report (only in HTML reports).

## Examples
1. **I want to generate a report of the 5 closest state House contests.**<br>
`python ./election_results.py --contest=NCH`

2. **I want to get the closest statewide contest in Dare County's primary election in 2020.**<br>
`python ./election_results.py --contest=COS --counties=Dare --election=20200303 --limit=1`

3. **I want to get all legislative contests in the most recent election where the margin of victory is less than 5%.**<br>
`python ./election_results.py --contest=NCH,NCS --method=percentage --margin=10.00`

4. **I want to get a spreadsheet of all judicial races in Wake County.**<br>
`python ./election_results.py --contest=JUD --counties=Wake --format=csv --output=judicial.csv`

5. **I want the latest information on super-close races throughout the state.**<br>
`python ./election_results.py --update`

## Contributing
Please do! Feel free to file an issue or a PR. If you're reporting a problem, please include as much information as possible so I can track down the issue.

## License
MIT License

Copyright (c) 2024 Arianna Story

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Credits
The [North Carolina State Board of Elections](https://ncsbe.gov) is awesome and provides easy access to it's structured data. You can take a look at the actual Election Results dashboard at https://er.ncsbe.gov/.