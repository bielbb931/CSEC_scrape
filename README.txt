CSEC Scraper (FMV CSEC certificates)

#Using Py 3.12.0 (download if necessary)

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

5) Output
   - Excel file at output\csec_products.xlsx
   - Columns: Certification ID, Validity, Product name, Product category,
              Insurance package, Certification date, Developer, ITSEF,
              Product URL, Certification report URL

How PDF parsing works (simple):
- The script downloads the Certification Report PDF file for each product.
- It extracts text, narrows to the section titled '2 Identification',
  and looks for a line that begins with 'ITSEF'. The text after 'ITSEF'
  (same line or the next line) is captured as the lab name.
- If the PDF is image-based or formatted differently, ITSEF may be blank.
