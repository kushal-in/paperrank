"""
Step 3 - find the ROR id of every NIRF institution (the join key for OpenAlex in the next step).

Matching rule (state this in the report)
  1. Query the ROR API (country India) with the NIRF name, or with a hand-written query from
     QUERY_OVERRIDE where the NIRF name is not how ROR spells it. No exact-phrase quotes, so
     "Calcutta University" can still find "University of Calcutta".
  2. Score every candidate:  name_score = best similarity between the query and any of the
     candidate's names/aliases;  score = name_score + 0.08 if the candidate's city equals the
     institution's cleaned NIRF city (capped at 1).
  3. Decision
       auto        score >= 0.90 and (city matches or lead over the 2nd candidate >= 0.02),
                   or (score >= 0.80, city matches, and lead over the 2nd candidate >= 0.15)
       review      score >= 0.75 (a person must confirm)
       review_low  best score below 0.75
       no_match    ROR returned nothing
  4. Whatever a person confirms goes in ror_manual.csv (columns: id_new, ror_id, note) and wins over
     the automatic decision. Keep that file: it is your record of the manual review.

Usage
  python 03_ror_match.py
  python 03_ror_match.py --input clean/institutions_2026-11-01.csv

Output
  interim/ror_candidates_<date>.csv   every candidate with its scores
  interim/ror_best_<date>.csv         one row per institution with the decision
"""
import argparse
import re
import sys
import time
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests

TODAY = date.today().isoformat()
CLEAN = Path("clean")
INTERIM = Path("interim")
API = "https://api.ror.org/v2/organizations"
COUNTRY_FILTER = "country.country_code:in"   # lower case worked in the first run
SLEEP_S = 0.25
KEEP = 8                                      # candidates stored per institution

# NIRF name (as in name_new) -> the name ROR actually uses. Extend this as the review file shows misses.
QUERY_OVERRIDE = {
    "calicut university": "University of Calicut",
    "kerala university": "University of Kerala",
    "mysore university": "University of Mysore",
    "calcutta university": "University of Calcutta",
    "college of engineering pune": "College of Engineering Pune COEP Technological University",
    "manipal academy of higher education manipal": "Manipal Academy of Higher Education",
    "shanmugha arts science technology and research academy": "SASTRA Shanmugha Arts Science Technology Research Academy",
    "indian institute of technology (indian school of mines)": "Indian Institute of Technology (Indian School of Mines) Dhanbad",
    "s r m institute of science and technology": "SRM Institute of Science and Technology",
    "national institute of technology karnataka surathkal": "National Institute of Technology Karnataka",
    "andhra university visakhapatnam": "Andhra University",
    "thapar institute of engineering and technology (deemed to be university)": "Thapar Institute of Engineering and Technology",
    "dr d y patil vidyapeeth": "Dr. D. Y. Patil Vidyapeeth Pune",
    "king george s medical university": "King George's Medical University",
    "mahatma gandhi university kottayam": "Mahatma Gandhi University",
    "g b pant universtiy of agriculture and technology": "Govind Ballabh Pant University of Agriculture and Technology",
    "psg institute of medical sciences and research": "PSG Institute of Medical Sciences and Research",
    "svkm s narsee monjee institute of management studies": "SVKM's Narsee Monjee Institute of Management Studies",
    "koneru lakshmaiah education foundation university (k l college of engineering)": "Koneru Lakshmaiah Education Foundation",
    "visvesvaraya national institute of technology nagpur": "Visvesvaraya National Institute of Technology Nagpur",
    "all india institute of medical sciences delhi": "All India Institute of Medical Sciences New Delhi",
    "babasheb bhimrao ambedkar university": "Babasaheb Bhimrao Ambedkar University",
    "indian statistical institute kolkata": "Indian Statistical Institute",
    "national institute of mental health and neuro sciences bangalore": "National Institute of Mental Health and Neurosciences",
    "sher e kashmir university of agricultural science and technology of kashmir":
        "Sher-e-Kashmir University of Agricultural Sciences and Technology of Kashmir",
    "national institute of pharmaceutical education and research hyderabad":
        "National Institute of Pharmaceutical Education and Research Hyderabad",
    "university of agricultural sciences": "University of Agricultural Sciences Dharwad",
}


def fold(s):
    """lower case, no accents, no punctuation, '(deemed ...)' dropped, 'the' dropped"""
    if not isinstance(s, str):      # NaN / None (a missing city)
        s = ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\(deemed[^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(t for t in s.split() if t != "the")


def sim(a, b):
    """Order-sensitive similarity. (An earlier version also took a word-set overlap, which scored
    'Post Graduate Institute of Medical Education and Research' and 'Institute of Post Graduate Medical
    Education and Research' as identical and picked the Kolkata institute for PGIMER Chandigarh.)"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def search(session, query):
    for attempt in range(4):
        r = session.get(API, params={"query": query, "filter": COUNTRY_FILTER}, timeout=30)
        if r.status_code == 429:
            time.sleep(5 * 2 ** attempt)
            continue
        r.raise_for_status()
        return r.json().get("items", [])
    raise RuntimeError("ROR is still rate limiting after 4 tries - wait a few minutes and rerun")


def parse(item):
    names = item.get("names", [])
    display = next(
        (n["value"] for n in names if "ror_display" in n.get("types", [])),
        names[0]["value"] if names else "",
    )
    loc = (item.get("locations") or [{}])[0].get("geonames_details", {})
    return {
        "ror_id": item.get("id"),
        "ror_name": display,
        "ror_city": loc.get("name"),
        "status": item.get("status"),
        "types": ";".join(item.get("types", [])),
        "_names": [n["value"] for n in names if "acronym" not in n.get("types", [])],
    }


def score_candidates(query, city, items):
    q, c = fold(query), fold(city)
    out = []
    for item in items:
        cand = parse(item)
        name_score = max((sim(q, fold(n)) for n in cand["_names"]), default=0.0)
        city_match = bool(c) and fold(cand["ror_city"]) == c
        cand["name_score"] = round(name_score, 3)
        cand["city_match"] = city_match
        cand["score"] = round(min(1.0, name_score + (0.08 if city_match else 0.0)), 3)
        del cand["_names"]
        out.append(cand)
    # equal scores (the city bonus is capped at 1.0): the candidate in the right city goes first
    out.sort(key=lambda x: (x["score"], x["city_match"], x["name_score"]), reverse=True)
    return out


def decide(cands):
    if not cands:
        return "no_match", 0.0
    best = cands[0]
    margin = best["score"] - (cands[1]["score"] if len(cands) > 1 else 0.0)
    # a tie at the top with no city match is ambiguous (e.g. two 'Mahatma Gandhi University' records)
    if best["score"] >= 0.90 and (best["city_match"] or margin >= 0.02):
        return "auto", margin
    if best["score"] >= 0.80 and best["city_match"] and margin >= 0.15:
        return "auto", margin
    if best["score"] >= 0.75:
        return "review", margin
    return "review_low", margin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="institutions CSV from step 2 (default: newest in clean/)")
    args = ap.parse_args()

    INTERIM.mkdir(exist_ok=True)
    if args.input:
        path = Path(args.input)
    else:
        files = sorted(CLEAN.glob("institutions_*.csv"))
        if not files:
            sys.exit("no clean/institutions_*.csv - run step 2 first")
        path = files[-1]
    inst = pd.read_csv(path)
    print(f"{len(inst)} institutions from {path}")

    manual = {}
    if Path("ror_manual.csv").exists():
        m = pd.read_csv("ror_manual.csv")
        manual = dict(zip(m["id_new"], m["ror_id"]))
        print(f"{len(manual)} manual decisions read from ror_manual.csv")

    session = requests.Session()
    cand_rows, best_rows, used = [], [], set()
    for n, row in enumerate(inst.itertuples(index=False), start=1):
        query = QUERY_OVERRIDE.get(row.name_new, row.name_new)
        if row.name_new in QUERY_OVERRIDE:
            used.add(row.name_new)
        items = search(session, query)
        if not items and "(" in query:
            items = search(session, re.sub(r"\(.*?\)", " ", query))
        cands = score_candidates(query, row.location_clean, items)[:KEEP]
        decision, margin = decide(cands)

        for rank_in_list, c in enumerate(cands, start=1):
            cand_rows.append({"id_new": row.id_new, "rank_in_list": rank_in_list, "query": query, **c})

        best = cands[0] if cands else {}
        ror_id = best.get("ror_id")
        ror_name = best.get("ror_name")
        if row.id_new in manual:
            ror_id, decision = manual[row.id_new], "manual"
            ror_name = next((c["ror_name"] for c in cands if c["ror_id"] == ror_id), None)
        best_rows.append({
            "id_new": row.id_new, "name_new": row.name_new, "location_clean": row.location_clean,
            "query": query, "decision": decision, "ror_id": ror_id, "ror_name": ror_name,
            "ror_city": best.get("ror_city"), "score": best.get("score"),
            "margin": round(margin, 3), "n_candidates": len(items),
        })
        if n % 25 == 0:
            print(f"  {n}/{len(inst)}")
        time.sleep(SLEEP_S)

    pd.DataFrame(cand_rows).to_csv(INTERIM / f"ror_candidates_{TODAY}.csv", index=False)
    best_df = pd.DataFrame(best_rows)
    best_df.to_csv(INTERIM / f"ror_best_{TODAY}.csv", index=False)

    print("\ndecisions:")
    print(best_df["decision"].value_counts().to_string())
    todo = best_df[best_df["decision"].isin(["review", "review_low", "no_match"])]
    print(f"\n{len(todo)} institutions need a person. Open interim/ror_candidates_{TODAY}.csv, pick the right "
          "ror_id for each, and list it in ror_manual.csv (id_new, ror_id, note). Then rerun this script.")
    unused = sorted(set(QUERY_OVERRIDE) - used)
    if unused:
        print("\nQUERY_OVERRIDE keys that matched no institution (typo, or already renamed in step 2):")
        for k in unused:
            print("  -", k)


if __name__ == "__main__":
    main()
