CSEC Scraper (FMV CSEC certificates)

#Create & activate a virtual environment (Windows PowerShell)
> py -3.12 -m venv .venv
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1

#Install dependencies and Playwright browsers
> python -m pip install -r requirements.txt
> python -m playwright install

#Watch the browser work
> $env:HEADLESS="0"

#Run the scraper
> python scripts\run_csec.py



How PDF parsing works (simplified):
- The script navigates to CSEC certified products website and clicks into every product link
- Extracts information each specific product table (including Certification ID, Product Name, Certification date)
...The evaluation company is listed in the table but sometimes differs from the certification report - to get the evaluation company directly from the report pdf the script:
- Downloads the Certification Report PDF file for each product
- operates a 2 stage pdf extraction process:
	1: if the line starts with ITSEF and the value is on the same line → Stage A returns that value (no table assumptions as formatting is not a table).If a report wraps the value to the next line (or two), Stage A assembles those continuation lines until the next label.
	2: If line-breaking is weird, Stage B uses x/y coordinates: it finds the ITSEF label line and returns the text to its right on the same y-line (i.e., the visual “cell” next to it).
	In both stages, we reject lines containing “Security Target”, “document version…”, CC tokens (EAL/ALC/AVA…), Developer, Sponsor, Common Criteria version, CEM version, QMS version, “3.1 release 5”
