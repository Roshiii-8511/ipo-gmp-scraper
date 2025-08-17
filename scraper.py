# scraper.py
# Simple GMP scraper - beginner friendly
# 1) Edit URL below to the page you want to scrape.
# 2) If possible, edit NAME_CSS and GMP_CSS to exact CSS selectors (see instructions below).
# 3) Commit this file to your repo, then we'll add GitHub Actions next.

import requests, json, re
from bs4 import BeautifulSoup
from datetime import datetime

# -------------- CONFIG - edit these ----------------
URL = "https://example.com/ipo-gmp-page"   # <<< CHANGE THIS to real GMP page
# If you can copy CSS selectors, put them here (optional)
NAME_CSS = ""   # e.g. "table.gmp-table tbody tr td:nth-child(1)"
GMP_CSS  = ""   # e.g. "table.gmp-table tbody tr td:nth-child(2)"
# If NAME_CSS/GMP_CSS left empty, script will try to auto-detect the largest table on the page.
# ---------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0"
}

def normalize_num(s):
    if not s: return None
    s = s.replace(",", "").replace("₹", "").replace("Rs.", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

def scrape_once():
    print("Fetching:", URL)
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    rows = []

    if NAME_CSS and GMP_CSS:
        names = soup.select(NAME_CSS)
        gmps  = soup.select(GMP_CSS)
        for n, g in zip(names, gmps):
            text_name = n.get_text(strip=True)
            text_gmp  = g.get_text(strip=True)
            rows.append({"ipo": text_name, "gmp_raw": text_gmp, "gmp": normalize_num(text_gmp)})
    else:
        # Auto-detect the biggest table on the page
        tables = soup.select("table")
        best_table = None
        max_tr = 0
        for t in tables:
            tr_count = len(t.select("tr"))
            if tr_count > max_tr:
                max_tr = tr_count
                best_table = t
        if best_table:
            for tr in best_table.select("tr")[1:]:  # skip header row
                tds = tr.select("td")
                if len(tds) >= 2:
                    name = tds[0].get_text(strip=True)
                    gmp_raw = tds[1].get_text(strip=True)
                    rows.append({"ipo": name, "gmp_raw": gmp_raw, "gmp": normalize_num(gmp_raw)})

    data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": URL,
        "count": len(rows),
        "gmp_list": rows
    }

    with open("gmp.json", "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Saved gmp.json with", len(rows), "records")

if __name__ == "__main__":
    try:
        scrape_once()
    except Exception as e:
        print("Error:", e)
        # write a minimal JSON so workflow doesn't fail silently
        with open("gmp.json", "w", encoding="utf8") as f:
            json.dump({"last_updated": datetime.utcnow().isoformat()+"Z", "error": str(e), "gmp_list": []}, f, indent=2)
        raise
