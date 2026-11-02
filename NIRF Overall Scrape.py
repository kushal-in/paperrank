"""
Step 1 - scrape the NIRF "Overall" ranking tables, 2017-2025.

Changes versus the notebook version
  * The raw HTML of every year is saved untouched in raw/ (name = source_year_collectiondate),
    so the raw files are never edited and the collection date is on record.
  * robots.txt is fetched and saved, and printed, so the relevant lines can be quoted in the report.
  * The rank is READ FROM THE PAGE. Row order is used only if the rank cell is not a number,
    and any disagreement between the two is reported (this is what the 101-row 2020 table needs).
  * All five parameter scores (TLR, RPC, GO, OI, PR) are kept, not just RPC.
  * The undefined counter (num0) is gone; skipped rows are counted and printed.

Output
  raw/nirf_robots_<date>.txt
  raw/nirf_overall_<year>_<date>.html
  interim/nirf_overall_scraped_<date>.csv     one row per institution-year

Run:  python 01_scrape_nirf_overall.py
Needs: pandas, requests, beautifulsoup4
"""
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

YEARS = range(2017, 2026)
BASE = "https://www.nirfindia.org"
PAGE = BASE + "/Rankings/{year}/OverallRanking.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0"}
DELAY_S = 1.5
TODAY = date.today().isoformat()

# order of the numbers in the 'More Details' block of each row (the notebook used index 1 = RPC)
PARAMS = ["tlr", "rpc", "go", "oi", "pr"]

RAW = Path("raw")
INTERIM = Path("interim")


def to_float(text):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return None


def to_int(text):
    m = re.fullmatch(r"\s*(\d+)\s*", text or "")
    return int(m.group(1)) if m else None


def save_robots(session):
    r = session.get(BASE + "/robots.txt", headers=HEADERS, timeout=30)
    (RAW / f"nirf_robots_{TODAY}.txt").write_text(r.text, encoding="utf-8")
    print(f"robots.txt -> HTTP {r.status_code}")
    print(r.text[:2000])
    print("-" * 60)


def hidden_scores(hidden):
    """Parameter scores from the 'More Details' block of one row, as {param: float}."""
    if hidden is None:
        return {}
    values = [td.get_text(strip=True) for td in hidden.select("tbody tr td")]
    heads = [th.get_text(strip=True).lower() for th in hidden.select("thead th")]
    if heads and len(heads) == len(values):
        named = {}
        for head, value in zip(heads, values):
            for p in PARAMS:
                if head.startswith(p):
                    named[p] = to_float(value)
        if len(named) == len(PARAMS):
            return named
    # header names not usable: fall back to the positional order the notebook relied on
    return {p: to_float(v) for p, v in zip(PARAMS, values)}


def parse_year(html, year):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("tbody")
    if body is None:
        raise RuntimeError(f"{year}: no <tbody> found - the page layout changed")
    records, skipped = [], 0
    for row in body.find_all("tr", recursive=False):
        tds = row.find_all("td", recursive=False)
        if len(tds) != 6:
            skipped += 1
            continue
        name_cell = tds[1]
        first = name_cell.contents[0]
        name = first.get_text(strip=True) if hasattr(first, "get_text") else str(first).strip()
        scores = hidden_scores(name_cell.find("div", class_="tbl_hidden"))
        records.append({
            "year": year,
            "nirf_id": tds[0].get_text(strip=True),
            "name": name,
            "location": tds[2].get_text(strip=True),
            "rank_page": to_int(tds[5].get_text(strip=True)),
            "cell_3": tds[3].get_text(strip=True),   # kept raw for checking which td is which
            "cell_4": tds[4].get_text(strip=True),
            "cell_5": tds[5].get_text(strip=True),
            **{p: scores.get(p) for p in PARAMS},
        })
    for position, rec in enumerate(records, start=1):
        rec["rank_order"] = position
    if not records:
        raise RuntimeError(f"{year}: table found but no 6-column rows parsed")
    return pd.DataFrame(records), skipped


def main():
    RAW.mkdir(exist_ok=True)
    INTERIM.mkdir(exist_ok=True)
    session = requests.Session()
    save_robots(session)
    time.sleep(DELAY_S)

    frames = []
    for year in YEARS:
        url = PAGE.format(year=year)
        r = session.get(url, headers=HEADERS, timeout=60)
        if r.status_code != 200:
            sys.exit(f"{year}: HTTP {r.status_code} for {url}")
        (RAW / f"nirf_overall_{year}_{TODAY}.html").write_bytes(r.content)
        df, skipped = parse_year(r.text, year)
        print(f"{year}: {len(df)} rows parsed, {skipped} rows skipped")
        frames.append(df)
        time.sleep(DELAY_S)

    df = pd.concat(frames, ignore_index=True)
    df["rank_page"] = pd.to_numeric(df["rank_page"], errors="coerce")
    df["rank"] = df["rank_page"].fillna(df["rank_order"]).astype(int)
    df["score"] = df["rpc"]   # same meaning as the notebook's 'score' column (research score, RPC)

    out = INTERIM / f"nirf_overall_scraped_{TODAY}.csv"
    df.to_csv(out, index=False)
    print(f"\nsaved {len(df)} rows -> {out}")

    print("\nCheck the cells once by eye (is cell_5 really the rank?):")
    print(df[["year", "name", "cell_3", "cell_4", "cell_5", "rank_page", "rank_order"]].head(3).to_string(index=False))

    if df["rank_page"].isna().any():
        print(f"\nWARNING: rank cell is not a number for {df['rank_page'].isna().sum()} rows; row order was used "
              "for those. Open a saved HTML file and check which <td> holds the rank.")
    mismatch = df[df["rank_page"].notna() & (df["rank_page"] != df["rank_order"])]
    print(f"\nrows where the page rank differs from row order: {len(mismatch)}")
    if len(mismatch):
        print(mismatch[["year", "name", "rank_page", "rank_order"]].to_string(index=False))
    print("\nrows per year:")
    print(df.groupby("year").size().to_string())


if __name__ == "__main__":
    main()
