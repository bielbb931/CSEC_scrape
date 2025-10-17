# csec_scraper/csec_scraper.py
from __future__ import annotations
import os, re, io, typing, requests, pandas as pd
from dataclasses import dataclass
from playwright.sync_api import sync_playwright
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextBoxHorizontal, LTTextLineHorizontal

TARGET_URL = os.environ.get(
    "CSEC_URL",
    "https://www.fmv.se/verksamhet/ovrig-verksamhet/csec/certifikat-utgivna-av-csec/"
)

CANON_HEADERS = [
    "Listing name","Certification ID","Validity","Product name","Product category",
    "Insurance package","Certification date","Developer","ITSEF",
    "Product URL","Certification report URL",
]

def norm(s: typing.Optional[str]) -> str:
    return " ".join((s or "").replace("\xa0", " ").split()).strip()

ALIASES = {
    "certification id":"Certification ID","certifierings id":"Certification ID",
    "certifikat id":"Certification ID","certifikat-id":"Certification ID",
    "certifikatnummer":"Certification ID","certifieringsid":"Certification ID",
    "certifierings-id":"Certification ID","id":"Certification ID",
    "validity":"Validity","giltighet":"Validity",
    "product name":"Product name","produktnamn":"Product name","product":"Product name","produkt":"Product name",
    "product category":"Product category","produktkategori":"Product category",
    "insurance package":"Insurance package","försäkringspaket":"Insurance package",
    "certification date":"Certification date","certifieringsdatum":"Certification date","date of certification":"Certification date",
    "developer":"Developer","utvecklare":"Developer",
    "certification report":"Certification report","certifieringsrapport":"Certification report",
}

def to_canonical(h: str) -> typing.Optional[str]:
    key = norm(h).lower().rstrip(":")
    return ALIASES.get(key)

@dataclass
class ProductRow:
    Listing_name: str = ""
    Certification_ID: str = ""
    Validity: str = ""
    Product_name: str = ""
    Product_category: str = ""
    Insurance_package: str = ""
    Certification_date: str = ""
    Developer: str = ""
    ITSEF: str = ""
    Product_URL: str = ""
    Certification_report_URL: str = ""
    def to_dict(self):
        return {
            "Listing name": self.Listing_name, "Certification ID": self.Certification_ID or "NA",
            "Validity": self.Validity, "Product name": self.Product_name, "Product category": self.Product_category,
            "Insurance package": self.Insurance_package, "Certification date": self.Certification_date,
            "Developer": self.Developer, "ITSEF": self.ITSEF,
            "Product URL": self.Product_URL, "Certification report URL": self.Certification_report_URL,
        }

def _collect_list_links_with_titles(page) -> list[tuple[str,str]]:
    anchors = page.locator("main a, article a, section a")
    seen = set(); out = []
    for i in range(anchors.count()):
        a = anchors.nth(i); href = a.get_attribute("href") or ""; 
        if not href: continue
        text = norm(a.inner_text())
        if "csec" not in href.lower(): continue
        if href.startswith("/"):
            href = "https://www.fmv.se" + href
        href = href.split("#")[0]
        key = (href, text.lower())
        if href.startswith("https://www.fmv.se/") and key not in seen and text:
            seen.add(key); out.append((href, text))
    return out

def _extract_table_like_pairs(page) -> dict[str, dict]:
    result = {}
    tables = page.locator("table")
    for t in range(tables.count()):
        rows = tables.nth(t).locator("tr")
        for r in range(rows.count()):
            cells = rows.nth(r).locator("th,td")
            if cells.count() >= 2:
                h = norm(cells.nth(0).inner_text()); vloc = cells.nth(1)
                canon = to_canonical(h)
                if canon and canon not in result:
                    result[canon] = {"value": norm(vloc.inner_text()), "node": vloc}
    dts = page.locator("dt")
    for i in range(dts.count()):
        dt = dts.nth(i); h = norm(dt.inner_text()); canon = to_canonical(h)
        if not canon: continue
        vloc = dt.locator("xpath=following-sibling::*[1]")
        if vloc.count():
            result.setdefault(canon, {"value": norm(vloc.first.inner_text()), "node": vloc.first})
    rows = page.locator("li, .row, .grid, .c-table__row, .c-list__item, p, div")
    for i in range(min(rows.count(), 1200)):
        row = rows.nth(i); text = norm(row.inner_text())
        if ":" in text:
            label, val = [x.strip() for x in text.split(":", 1)]
            canon = to_canonical(label)
            if canon and canon not in result and val:
                result[canon] = {"value": val, "node": row}
    return result

def _value_after_label_block(page, label_variants: list[str]) -> str:
    lab_norm = [norm(l).lower().rstrip(":") for l in label_variants]
    xpath = " | ".join(
        f"//*[normalize-space(translate(string(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ','abcdefghijklmnopqrstuvwxyzåäö'))='{l}']"
        for l in lab_norm
    )
    lab = page.locator(f"xpath=({xpath})")
    if lab.count() == 0: return ""
    node = lab.first
    for sel in ["xpath=following::*[1]","xpath=following::*[self::p or self::div or self::td or self::li][1]","xpath=parent::*/following::*[1]"]:
        try:
            v = node.locator(sel)
            if v.count():
                txt = norm(v.first.inner_text())
                if txt: return txt
        except Exception: pass
    return ""

def _find_pdf_url(value_node) -> str:
    if not value_node: return ""
    try:
        aloc = value_node.locator("a[href$='.pdf'], a[href*='.pdf'], a:has-text('PDF')")
        if aloc.count():
            href = aloc.first.get_attribute("href") or ""
            if href.startswith("/"):
                href = "https://www.fmv.se" + href
            return href
    except Exception: pass
    return ""

_IDENT_LABELS = [
    "Certification Identification","Certification ID","Name and version of the certified IT product",
    "Security Target Identification","EAL","Sponsor","Developer","ITSEF",
    "Common Criteria version","CEM version","QMS version","Scheme Notes",
    "Recognition Scope","Certification date",
]
_LABEL_START = re.compile(r"^\s*(%s)\s*:?\s*$" % "|".join(re.escape(x) for x in _IDENT_LABELS), flags=re.IGNORECASE)
_CC_TOKENS = r"\b(EAL|ALC|ADV|ATE|AVA|ASE|ACO|AGD)\b"
_EXCLUDE_NEARBY_PATTERNS = [
    r"\bdocument version\b", r"\bDeveloper\b", r"\bSponsor\b", r"\b3\.1\s*release\s*5\b",
    r"\bCommon\s+Criteria\s+version\b", r"\bCEM\s+version\b", r"\bQMS\s+version\b",
    r"\bSecurity\s+Target\b", r"\bTarget\b",
]

def _is_bad_value(v: str) -> bool:
    if not v: return True
    if re.search(_CC_TOKENS, v, re.IGNORECASE): return True
    for pat in _EXCLUDE_NEARBY_PATTERNS:
        if re.search(pat, v, re.IGNORECASE): return True
    return False

def _slice_identification_section(full_text: str) -> str:
    m = re.search(r"\n\s*2\s+Identification\b", full_text, flags=re.IGNORECASE)
    if not m: return full_text
    start = m.start()
    m2 = re.search(r"\n\s*3[\.\s]", full_text[m.end():])
    end = m.end() + (m2.start() if m2 else 8000)
    return full_text[start:end]

def _extract_itsef_text_mode(pdf_bytes: bytes) -> str:
    txt = extract_text(io.BytesIO(pdf_bytes)) or ""
    txt = txt.replace("\u00ad", "")
    sec = _slice_identification_section(txt)
    lines = [" ".join(l.split()) for l in sec.splitlines()]

    for ln in lines:
        m = re.match(r"^\s*ITSEF\b[:\-\s]*(.+)$", ln, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip(" .;-")
            if not _is_bad_value(val): return val

    for i, ln in enumerate(lines):
        if re.fullmatch(r"\s*ITSEF\s*[:\-]?\s*", ln, flags=re.IGNORECASE):
            buf = []
            for j in range(i+1, min(i+8, len(lines))):
                nxt = lines[j].strip()
                if not nxt: break
                if _LABEL_START.match(nxt): break
                buf.append(nxt)
            val = " ".join(buf).strip(" .;-")
            if _is_bad_value(val) and len(buf) > 1:
                for k in range(len(buf)):
                    vv = " ".join(buf[k:]).strip(" .;-")
                    if not _is_bad_value(vv):
                        val = vv; break
            if val and not _is_bad_value(val): return val
    return ""

def _extract_itsef_layout_mode(pdf_bytes: bytes) -> str:
    try:
        for page_layout in extract_pages(io.BytesIO(pdf_bytes)):
            lines = []
            for obj in page_layout:
                if isinstance(obj, LTTextBoxHorizontal):
                    for line in obj:
                        if isinstance(line, LTTextLineHorizontal):
                            text = " ".join(line.get_text().replace("\u00ad","").split())
                            if not text: continue
                            lines.append((text, line.x0, line.x1, line.y0, line.y1))
            for text, x0, x1, y0, y1 in lines:
                if re.search(r"\bITSEF\b", text, flags=re.IGNORECASE):
                    row_vals = []
                    for t2, a0, a1, b0, b1 in lines:
                        same_row = abs(((y0 + y1)/2) - ((b0 + b1)/2)) < 2.2
                        to_right = a0 > x1 + 1.0
                        if same_row and to_right:
                            row_vals.append((a0, t2))
                    if row_vals:
                        row_vals.sort(key=lambda z: z[0])
                        candidate = " ".join(t for _, t in row_vals).strip(" .;-")
                        if candidate and not _is_bad_value(candidate): return candidate
        return ""
    except Exception:
        return ""

def _extract_itsef_from_pdf(pdf_url: str) -> str:
    if not pdf_url: return ""
    try:
        resp = requests.get(pdf_url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        resp.raise_for_status()
        pdf_bytes = resp.content
    except Exception:
        return ""

    val = _extract_itsef_text_mode(pdf_bytes)
    if val and not _is_bad_value(val): return val
    val = _extract_itsef_layout_mode(pdf_bytes)
    if val and not _is_bad_value(val): return val
    return ""

def _find_pdf_url(value_node) -> str:
    if not value_node: return ""
    try:
        aloc = value_node.locator("a[href$='.pdf'], a[href*='.pdf'], a:has-text('PDF')")
        if aloc.count():
            href = aloc.first.get_attribute("href") or ""
            if href.startswith("/"):
                href = "https://www.fmv.se" + href
            return href
    except Exception: pass
    return ""

def run(headless: bool = True, out_xlsx: str = "output/csec_products.xlsx") -> int:
    os.makedirs(os.path.dirname(out_xlsx), exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_load_state("networkidle")

        link_title_pairs = _collect_list_links_with_titles(page)
        if not link_title_pairs:
            raise RuntimeError("No product links found on the CSEC list page.")

        for link, listing_name in link_title_pairs:
            page.goto(link, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_load_state("networkidle")

            pairs = _extract_table_like_pairs(page)

            cert_id = pairs.get("Certification ID", {}).get("value", "")
            if not cert_id:
                cert_id = _value_after_label_block(page, [
                    "Certifierings ID", "Certification ID",
                    "Certifikat ID", "Certifikat-ID", "Certifikatnummer"
                ])
            if not cert_id:
                cert_id = "NA"

            cert_report_node = pairs.get("Certification report", {}).get("node", None)
            pdf_url = _find_pdf_url(cert_report_node)
            itsef = _extract_itsef_from_pdf(pdf_url)

            rec = {
                "Listing name": listing_name,
                "Certification ID": cert_id,
                "Validity": pairs.get("Validity", {}).get("value", ""),
                "Product name": pairs.get("Product name", {}).get("value", ""),
                "Product category": pairs.get("Product category", {}).get("value", ""),
                "Insurance package": pairs.get("Insurance package", {}).get("value", ""),
                "Certification date": pairs.get("Certification date", {}).get("value", ""),
                "Developer": pairs.get("Developer", {}).get("value", ""),
                "ITSEF": itsef,
                "Product URL": link,
                "Certification report URL": pdf_url or "",
            }
            rows.append(rec)

        browser.close()

    df = pd.DataFrame(rows, columns=CANON_HEADERS)
    df.to_excel(out_xlsx, index=False)
    print(f"Saved {len(rows)} rows to {out_xlsx}")
    return len(rows)

if __name__ == "__main__":
    headless = os.environ.get("HEADLESS", "1") != "0"
    out_xlsx = os.environ.get("OUT_XLSX", "output/csec_products.xlsx")
    run(headless=headless, out_xlsx=out_xlsx)
