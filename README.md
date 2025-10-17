CSEC Scraper (CC certificates)

#Quick start
~ Requires Python 3.12.0

#Download and extract zip file from: https://github.com/bielbb931/CSEC_scrape.git

#Windows (PowerShell)
~open powershell terminal in 

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

# Output file:
> .\output\csec_products.xlsx


