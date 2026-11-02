"""
Step 4 - OpenAlex: publication and citation counts for every institution that step 3 matched to a ROR id.

Source: https://api.openalex.org  (docs: https://developers.openalex.org)
Authentication: optional `api_key` query parameter. A free key (openalex.org/settings/api) gives a larger
daily budget than no key, and the budget refills at midnight UTC. Set it in your shell before running:
    export OPENALEX_API_KEY=your_key        (Windows PowerShell:  $env:OPENALEX_API_KEY="your_key")

What it collects, per institution
  1. The institution record, fetched by ROR id (a "singleton" call): OpenAlex id, name, type, country,
     city, lifetime works and citations, h-index, lineage (the institution and the units that roll up
     into it), and counts_by_year.
  2. Works per publication year from the works endpoint, grouped by publication_year, in five variants:
       works_all_lineage         all works whose author affiliation is this institution or a unit under it
       works_article_lineage     the same, articles only
       works_cited_ge1_lineage   the same, works cited at least once
       works_cited_ge10_lineage  the same, works cited at least ten times
       works_all_own             works that name this exact institution (no child units)
     Lineage vs own is a measurable choice: report both in the limitations.

Meaning of the citation columns (say this in the report)
  * oa_cited_by_count_year      citations RECEIVED in that calendar year, by any of the institution's works.
  * works_cited_ge1/ge10        lifetime citations of works PUBLISHED in that year, as of the collection date.
                                Older years have had longer to collect citations, so compare within a year
                                or use a fixed window, never raw across years.

Every response is saved untouched under raw/openalex/ with the collection date in its name, and a rerun on
the same day reuses those files instead of calling the API again (so an interrupted run costs nothing extra).
Nothing is filtered here: works dated in the future (2030, 2031...) are kept and flagged future_year, so the
outlier step can show them as errors before removing them.

Usage
  python 04_openalex_collect.py --limit 3          # try three institutions first
  python 04_openalex_collect.py                    # all institutions with decision auto/manual
  python 04_openalex_collect.py --include-review   # also the ones step 3 left for review (flagged)

Output
  raw/openalex/openalex_<ror>_<call>_<date>.json
  interim/openalex_institutions_<date>.csv   one row per institution
  interim/openalex_yearly_<date>.csv         one row per institution-year (long format)
  interim/openalex_crosswalk_<date>.csv      NIRF id -> ROR id -> OpenAlex id (the join table)
  interim/ror_duplicates_<date>.csv          NIRF institutions that resolved to the same ROR id
"""
import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://api.openalex.org"
TODAY = date.today().isoformat()
THIS_YEAR = date.today().year
SLEEP_S = 0.15               # stays far below the 100 requests/second limit
CACHE = Path("raw") / "openalex"
INTERIM = Path("interim")

# output column -> works filter. {oid} is the OpenAlex id (I123...) of the institution.
VARIANTS = {
    "works_all_lineage": "authorships.institutions.lineage:{oid}",
    "works_article_lineage": "authorships.institutions.lineage:{oid},type:article",
    "works_cited_ge1_lineage": "authorships.institutions.lineage:{oid},cited_by_count:>0",
    "works_cited_ge10_lineage": "authorships.institutions.lineage:{oid},cited_by_count:>9",
    "works_all_own": "authorships.institutions.id:{oid}",
}


class BudgetExhausted(Exception):
    pass


def short_id(url):
    return str(url).rstrip("/").rsplit("/", 1)[-1]


def get_json(session, path, params, cache_file):
    """GET one API call, with a same-day file cache. Returns the decoded JSON.
    A 404 is stored as {"_status": 404} so it is not asked again."""
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    params = dict(params)
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key

    for attempt in range(5):
        r = session.get(BASE + path, params=params, timeout=60)
        if r.status_code == 404:
            data = {"_status": 404}
            break
        if r.status_code == 429:
            # too many requests per second, or the daily budget is used up
            if attempt >= 2:
                raise BudgetExhausted(r.text[:300])
            time.sleep(5 * 2 ** attempt)
            continue
        if r.status_code >= 500:
            time.sleep(3 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json()
        break
    else:
        raise RuntimeError(f"OpenAlex kept failing for {path} {params.get('filter', '')}")

    cache_file.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(SLEEP_S)
    return data


def works_by_year(session, filter_str, cache_file):
    data = get_json(session, "/works", {"filter": filter_str, "group_by": "publication_year"}, cache_file)
    groups = data.get("group_by", [])
    expected = (data.get("meta") or {}).get("groups_count")
    if expected and len(groups) < expected:
        print(f"    WARNING: only {len(groups)} of {expected} year-groups returned for {filter_str}")
    out = {}
    for g in groups:
        try:
            out[int(g["key"])] = int(g["count"])
        except (KeyError, ValueError, TypeError):
            continue          # the 'unknown' year group
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="ror_best CSV from step 3 (default: newest in interim/)")
    ap.add_argument("--include-review", action="store_true",
                    help="also process institutions step 3 marked review / review_low")
    ap.add_argument("--limit", type=int, help="only the first N institutions (a cheap trial run)")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(exist_ok=True)

    if args.input:
        path = Path(args.input)
    else:
        files = sorted(INTERIM.glob("ror_best_*.csv"))
        if not files:
            sys.exit("no interim/ror_best_*.csv - run step 3 first")
        path = files[-1]
    best = pd.read_csv(path)
    print(f"{len(best)} institutions in {path}")

    keep = ["auto", "manual"] + (["review", "review_low"] if args.include_review else [])
    todo = best[best["decision"].isin(keep) & best["ror_id"].notna()].copy()
    print(f"{len(todo)} with decision in {keep}; the other {len(best) - len(todo)} are skipped")

    dups = todo[todo.duplicated("ror_id", keep=False)].sort_values("ror_id")
    if len(dups):
        dups.to_csv(INTERIM / f"ror_duplicates_{TODAY}.csv", index=False)
        print(f"WARNING: {len(dups)} NIRF institutions share a ROR id with another; they are fetched once. "
              f"See interim/ror_duplicates_{TODAY}.csv and fix them in step 3 (ror_manual.csv).")

    rors = todo.drop_duplicates("ror_id")
    if args.limit:
        rors = rors.head(args.limit)
    n_calls = len(rors) * (1 + len(VARIANTS))
    print(f"{len(rors)} distinct ROR ids -> about {n_calls} requests "
          f"({'with' if os.environ.get('OPENALEX_API_KEY') else 'WITHOUT'} an API key; "
          "set OPENALEX_API_KEY to get the larger daily budget)\n")

    session = requests.Session()
    inst_rows, year_rows, crosswalk = [], [], []
    stopped_early = False

    for n, row in enumerate(rors.itertuples(index=False), start=1):
        ror_short = short_id(row.ror_id)
        try:
            inst = get_json(session, f"/institutions/ror:{ror_short}", {},
                            CACHE / f"openalex_{ror_short}_institution_{TODAY}.json")
            if inst.get("_status") == 404:
                print(f"[{n}/{len(rors)}] {row.name_new}: not found in OpenAlex ({row.ror_id})")
                inst_rows.append({"ror_id": row.ror_id, "status": "not_in_openalex", "retrieved_on": TODAY})
                continue

            oid = short_id(inst["id"])
            per_col = {}
            for col, template in VARIANTS.items():
                per_col[col] = works_by_year(
                    session, template.format(oid=oid),
                    CACHE / f"openalex_{ror_short}_{col}_{TODAY}.json")
        except BudgetExhausted as e:
            print(f"\nSTOPPED at institution {n}: OpenAlex answered 429 (rate or daily budget). {e}")
            print("Everything fetched so far is cached. Set OPENALEX_API_KEY (free key) or wait until "
                  "midnight UTC, then rerun the same command - it resumes from the cache.")
            stopped_early = True
            break

        stats = inst.get("summary_stats") or {}
        geo = inst.get("geo") or {}
        own_total = sum(per_col["works_all_own"].values())
        works_count = inst.get("works_count")
        ratio = round(own_total / works_count, 4) if works_count else None
        returned_ror = short_id(inst.get("ror") or "")
        lineage = [short_id(x) for x in inst.get("lineage", [])]

        inst_rows.append({
            "ror_id": row.ror_id,
            "openalex_id": oid,
            "display_name": inst.get("display_name"),
            "type": inst.get("type"),
            "country_code": inst.get("country_code"),
            "city": geo.get("city"),
            "works_count_total": works_count,
            "cited_by_count_total": inst.get("cited_by_count"),
            "h_index": stats.get("h_index"),
            "two_yr_mean_citedness": stats.get("2yr_mean_citedness"),
            "lineage": ";".join(lineage),
            "n_lineage": len(lineage),
            "ror_returned_differs": bool(returned_ror) and returned_ror != ror_short,
            "own_total_over_works_count": ratio,
            "status": "ok",
            "source_url": f"{BASE}/institutions/ror:{ror_short}",
            "retrieved_on": TODAY,
        })

        by_year = {c.get("year"): c for c in inst.get("counts_by_year", []) if c.get("year") is not None}
        years = sorted(set().union(*[set(d) for d in per_col.values()], set(by_year)))
        for y in years:
            year_rows.append({
                "ror_id": row.ror_id,
                "openalex_id": oid,
                "year": y,
                **{col: per_col[col].get(y, 0) for col in VARIANTS},
                "oa_works_count_year": by_year.get(y, {}).get("works_count"),
                "oa_cited_by_count_year": by_year.get(y, {}).get("cited_by_count"),
                "future_year": y > THIS_YEAR,
            })

        print(f"[{n}/{len(rors)}] {row.name_new} -> {oid} {inst.get('display_name')} "
              f"({works_count} works, lineage {len(lineage)})")

    inst_df = pd.DataFrame(inst_rows)
    year_df = pd.DataFrame(year_rows)
    inst_df.to_csv(INTERIM / f"openalex_institutions_{TODAY}.csv", index=False)
    year_df.to_csv(INTERIM / f"openalex_yearly_{TODAY}.csv", index=False)

    if len(inst_df) and "openalex_id" in inst_df:
        oa = inst_df.dropna(subset=["openalex_id"])[["ror_id", "openalex_id"]]
        cw = todo[["id_new", "name_new", "decision", "ror_id"]].merge(oa, on="ror_id", how="left")
        cw.to_csv(INTERIM / f"openalex_crosswalk_{TODAY}.csv", index=False)

    print("\n--- summary ---")
    print(f"institutions fetched: {int((inst_df.get('status') == 'ok').sum()) if len(inst_df) else 0}"
          f"{' (run stopped early)' if stopped_early else ''}")
    if len(inst_df):
        print(f"not in OpenAlex: {int((inst_df['status'] == 'not_in_openalex').sum())}")
        ok = inst_df[inst_df["status"] == "ok"]
        bad_ratio = ok[(ok["own_total_over_works_count"] < 0.98) | (ok["own_total_over_works_count"] > 1.02)]
        print(f"own-works total differs >2% from the institution's works_count: {len(bad_ratio)} "
              "(check these: unknown-year works or a merged record)")
        print(f"ROR id returned differs from the one asked (merged record): {int(ok['ror_returned_differs'].sum())}")
        big = ok[ok["n_lineage"] > 1]
        print(f"institutions with child units in their lineage: {len(big)}")
    if len(year_df):
        fut = year_df[year_df["future_year"]]
        print(f"works dated after {THIS_YEAR}: {int(fut['works_all_lineage'].sum())} across "
              f"{fut['year'].nunique()} future years - kept and flagged, to be shown as errors in the outlier step")
    print(f"\nwritten to {INTERIM}/ ; raw responses in {CACHE}/")


if __name__ == "__main__":
    main()
