# scraper.py
# Beginner-friendly GMP scraper.
# 1) Change URL to the page you want to scrape.
# 2) If table has headers like "Company" and "GMP", script will auto-find columns.
# 3) If that fails, you'll later paste CSS selectors (I'll show you how).

import requests, json, re
from bs4 import BeautifulSoup
from datetime import datetime

# ---------- EDIT THIS ----------
URL = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"   # <<< PUT target GMP page URL HERE
# -------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0"
}

def normalize_num(s):
    if not s: return None
    s = s.replace(",", "").replace("₹", "").replace("Rs.", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

def parse_table(table):
    rows_out = []
    trs = table.select("tr")
    if not trs:
        return rows_out
    # header detection
    header_cells = trs[0].select("th,td")
    headers = [h.get_text(strip=True).lower() for h in header_cells]
    # find probable columns
    def find_idx(possible):
        for i, h in enumerate(headers):
            for p in possible:
                if p in h:
                    return i
        return None

    name_idx = find_idx(["ipo", "company", "name", "issue"])
    gmp_idx  = find_idx(["gmp", "grey", "premium", "premium (₹)", "gmp(₹)"])
    # fallback: if not found, assume first column = name, second = gmp
    if name_idx is None or gmp_idx is None:
        if len(header_cells) >= 2:
            name_idx = 0 if name_idx is None else name_idx
            gmp_idx  = 1 if gmp_idx is None else gmp_idx
        else:
            return rows_out

    # parse rows
    for tr in trs[1:]:
        tds = tr.select("td")
        if len(tds) <= max(name_idx, gmp_idx):
            continue
        name = tds[name_idx].get_text(strip=True)
        gmp_raw = tds[gmp_idx].get_text(strip=True)
        rows_out.append({
            "ipo": name,
            "gmp_raw": gmp_raw,
            "gmp": normalize_num(gmp_raw)
        })
    return rows_out

def scrape_once():
    print("Fetching:", URL)
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    all_rows = []
    # try every table and pick the one with most rows
    tables = soup.select("table")
    best = []
    for t in tables:
        parsed = parse_table(t)
        if len(parsed) > len(best):
            best = parsed
    all_rows = best

    # fallback: try finding single GMP value elements (if page lists one)
    if not all_rows:
        # look for elements that contain 'gmp' text near numbers
        text = soup.get_text(" ", strip=True)
        m = re.findall(r"([A-Za-z0-9 &\-\_\.]{3,60})\s*(?:[:\-–])\s*₹?\s*(-?\d+)", text)
        for name, num in m:
            all_rows.append({"ipo": name.strip(), "gmp_raw": num, "gmp": normalize_num(num)})

    data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": URL,
        "count": len(all_rows),
        "gmp_list": all_rows
    }

    with open("gmp.json", "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved gmp.json with", len(all_rows), "records")

if __name__ == "__main__":
    try:
        scrape_once()
    except Exception as e:
        print("Error:", e)
        with open("gmp.json", "w", encoding="utf8") as f:
            json.dump({"last_updated": datetime.utcnow().isoformat()+"Z", "error": str(e), "gmp_list": []}, f, indent=2)
        raise
