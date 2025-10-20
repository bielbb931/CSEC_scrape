CSEC Scraper (FMV CSEC certificates)

#Using Py 3.12.0 (download if necessary)
...download zip file, extract, then open windows powershell terminal in extracted folder

1) Create & activate a virtual environment in Windows PowerShell:
     py -3.12 -m venv .venv
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     .\.venv\Scripts\Activate.ps1

2) Install dependencies and Playwright browsers
     python -m pip install -r requirements.txt
     python -m playwright install

3) Watch the browser work
     $env:HEADLESS="0"

4) Run the scraper
     python scripts\run_csec.py

*Note on pdf parsing. the ITSEF is given on the CSEC product page in table format however this is often inconsistent with the actual certification pdf (e.g. for "Re-evaluation of NetIQ® Sentinel™ 8.5.1.0" the product page states only "Combitech AB" as ITSEF, whereas pdf states "Combitech AB, Intertek/EWA-Canada") ... this is why we chose to integrate pdf parsing into python script. Also we knew that other scheme pages ONLY show certain info on certification pdf so this capability would be a must.
