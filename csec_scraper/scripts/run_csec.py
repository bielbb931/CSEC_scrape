# scripts/run_csec.py
from pathlib import Path
import sys, os
sys.path.append(str(Path(__file__).resolve().parents[1]))

from csec_scraper.csec_scraper import run

if __name__ == "__main__":
    headless = os.environ.get("HEADLESS", "1") != "0"
    out_xlsx = os.environ.get("OUT_XLSX", "output/csec_products.xlsx")
    run(headless=headless, out_xlsx=out_xlsx)
