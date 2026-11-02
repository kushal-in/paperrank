"""
Step 2 - clean the scraped NIRF table: one stable id per institution, one name, one location.

Matching rule (state this in the report)
  1. From 2018 on, NIRF ids end in a letter-number tail (IR-O-U-0456 -> U-0456). That tail is the id.
  2. The 2017 ids use another format and have no tail, so 2017 rows are matched BY NAME:
       a. normalised name looked up among the names of rows that do have an id;
       b. if that fails, a hand-checked alias (2017 spelling -> later spelling) is tried first;
       c. whatever is still unmatched gets a placeholder id X-0000, X-0001, ... (alphabetical),
          meaning "seen in 2017 only".
  3. name_new = the institution's most recent name.

Fixes versus the notebook
  * SSN College: the notebook set id_map[<name>] = <name>, which overwrote the real id C-16604, so the
    2017 row ended up with the NAME in the id column and an empty name_new. That line is gone, and the
    2017 typo ("subrmaniya") is an alias for the later spelling.
  * JSS: the 2017 "Jagadguru Sri Shivarathreeshwara University" (Mysore) is the same institution as
    "JSS Academy of Higher Education and Research" (U-0222, Mysore) from 2018. Added as an alias.
    VERIFY this once on the NIRF pages - it is the only alias that goes beyond a spelling change.
  * Location labels are standardised (see SPELLING and BY_ID). The raw label is kept in location_raw.
  * College of Engineering (C-41593, Pune) is renamed to its full name so ROR matching stops guessing.
  * Audit checks stop the script if an id is missing, malformed, or an id repeats within a year.

Usage
  python 02_build_clean.py
  python 02_build_clean.py --input interim/nirf_overall_scraped_2026-11-01.csv --compare my_clean.csv

Output
  clean/nirf_overall_clean_<date>.csv   one row per institution-year
  clean/institutions_<date>.csv         one row per institution (input of step 3)
  clean/my_clean_fixed.csv              same columns as the old my_clean.csv
  interim/cleaning_log_<date>.csv       one line per cleaning step with rows affected
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

TODAY = date.today().isoformat()
CLEAN = Path("clean")
INTERIM = Path("interim")

ID_TAIL = r"([A-Z]-\d+)$"
VALID_ID = r"[A-Z]-\d+"          # also matches the X-0000 placeholders

# 2017 spelling -> later spelling (both already normalised). Targets must exist among later-year names.
ALIASES = {
    "dr d y patil vidyapeeth pune": "dr d y patil vidyapeeth",
    "indian institute of science bangalore": "indian institute of science",
    "shanmugha arts science technology and research academy (sastra)": "shanmugha arts science technology and research academy",
    "siksha o anusandhan university": "siksha o anusandhan",
    "sri ramachandra university": "sri ramachandra institute of higher education and research",
    "sri sivasubrmaniya nadar college of engineering": "sri sivasubramaniya nadar college of engineering",
    "symbiosis international university": "symbiosis international",
    "thapar university": "thapar institute of engineering and technology",
    # VERIFY: renamed institution, same city. Remove this line if the NIRF pages say otherwise.
    "jagadguru sri shivarathreeshwara university": "jss academy of higher education and research",
}

# hand fixes to the display name, by id (VERIFY C-41593 against the NIRF page: it is COEP, Pune)
NAME_FIX_BY_ID = {"C-41593": "college of engineering pune"}

# location label -> one spelling, applied to every row
SPELLING = {
    "Aizwal": "Aizawl",
    "Bangalore": "Bengaluru",
    "Mysore": "Mysuru",
    "Allahabad": "Prayagraj",
    "Gautam Budh Nagar": "Gautam Buddha Nagar",
    "Kurushetra": "Kurukshetra",
    "Srivilliputtur": "Srivilliputhur",
    "Jammu Tawi": "Jammu",
    "Belgaum": "Belagavi",
}

# one agreed location per institution where the labels switch between places or spellings
BY_ID = {
    "U-0589": "Santiniketan",          # Visva-Bharati; 'Kolkata' in 2017-18
    "U-0584": "Howrah",                # IIEST; Shibpur is a locality of Howrah
    "U-0139": "Gandhinagar",           # IIT Gandhinagar; 'Ahmedabad' in 2017
    "U-0251": "Malappuram",            # University of Calicut; 'Calicut' in 2017
    "U-0642": "Gautam Buddha Nagar",   # Shiv Nadar University; Chithera / Dadri / district
    "U-0458": "Srivilliputhur",        # Kalasalingam; 'Krishnan Koil' and two spellings
    "C-16604": "Kalavakkam",           # SSN; 'Kancheepuram' was used 2018-2022
}

LOG = []


def log(step, rows, detail=""):
    LOG.append({"step": step, "rows_affected": int(rows), "detail": detail})
    print(f"  {step}: {int(rows)} rows. {detail}")


def normalise(name):
    s = str(name).strip().lower()
    s = re.sub(r"[\"'\-`!|:.,]", " ", s)
    s = s.replace("&", "and")
    return re.sub(r"\s+", " ", s).strip()


def latest(folder, pattern):
    files = sorted(folder.glob(pattern))
    if not files:
        sys.exit(f"no file matching {folder}/{pattern} - run the previous step first")
    return files[-1]


def build_ids(df):
    df["name_norm"] = df["name"].map(normalise)
    df["id_tail"] = df["nirf_id"].astype(str).str.extract(ID_TAIL)[0]

    with_tail = df.dropna(subset=["id_tail"]).sort_values("year", kind="stable")
    clash = with_tail.groupby("name_norm")["id_tail"].nunique()
    if (clash > 1).any():
        print("WARNING: one name carries several ids:", list(clash[clash > 1].index))
    name_to_id = with_tail.drop_duplicates("name_norm").set_index("name_norm")["id_tail"].to_dict()

    for old, target in ALIASES.items():
        if target not in name_to_id:
            print(f"WARNING: alias target not found among later names: {target!r} (for {old!r})")

    no_tail = df["id_tail"].isna()
    df["id_new"] = df["id_tail"]
    df.loc[no_tail, "id_new"] = df.loc[no_tail, "name_norm"].map(
        lambda n: name_to_id.get(ALIASES.get(n, n))
    )
    repaired = no_tail & df["id_new"].notna()
    aliased = repaired & df["name_norm"].isin(list(ALIASES))
    log("2017 rows matched to a later id by name", repaired.sum(), f"of which via alias: {int(aliased.sum())}")

    still = df["id_new"].isna()
    unresolved = sorted(df.loc[still, "name_norm"].unique())
    placeholder = {n: f"X-{i:04d}" for i, n in enumerate(unresolved)}
    df.loc[still, "id_new"] = df.loc[still, "name_norm"].map(placeholder)
    log("placeholder ids (institution not matched in later years)", still.sum(), f"{len(unresolved)} institutions")
    return df


def build_names(df):
    latest_name = (
        df.sort_values("year", kind="stable")
        .drop_duplicates("id_new", keep="last")
        .set_index("id_new")["name_norm"]
    )
    df["name_new"] = df["id_new"].map(latest_name)
    fixed = df["id_new"].map(NAME_FIX_BY_ID)
    df["name_new"] = fixed.fillna(df["name_new"])
    log("display name fixed by hand", fixed.notna().sum(), str(NAME_FIX_BY_ID))
    return df


def build_locations(df):
    df["location_raw"] = df["location"]
    spelled = df["location_raw"].map(SPELLING).fillna(df["location_raw"])
    df["location_clean"] = df["id_new"].map(BY_ID).fillna(spelled)
    log("location label standardised", (df["location_clean"] != df["location_raw"]).sum(),
        "raw label kept in location_raw")
    return df


def audit(df):
    problems = []
    if df["id_new"].isna().any():
        problems.append("rows without id_new")
    bad = ~df["id_new"].astype(str).str.fullmatch(VALID_ID)
    if bad.any():
        problems.append(f"{int(bad.sum())} ids with an unexpected format: {sorted(df.loc[bad, 'id_new'].unique())[:10]}")
    if df["name_new"].isna().any():
        problems.append(f"{int(df['name_new'].isna().sum())} rows without name_new")
    dup = df.duplicated(["id_new", "year"], keep=False)
    if dup.any():
        problems.append(f"{int(dup.sum())} rows share an (id, year): {sorted(df.loc[dup, 'id_new'].unique())[:10]}")
    per_year = df.groupby("year").size()
    odd = per_year[per_year != 100]
    if len(odd):
        print(f"NOTE: years without exactly 100 rows (check for ties on the NIRF page): {dict(odd)}")
    return problems


def compare(compat, old_path):
    old = pd.read_csv(old_path)
    m = compat.merge(old, on=["year", "rank"], how="outer", suffixes=("", "_old"), indicator=True)
    only = m[m["_merge"] != "both"]
    both = m[m["_merge"] == "both"]
    changed = both[
        both["name_new"].fillna("").ne(both["name_new_old"].fillna(""))
        | both["score"].ne(both["score_old"])
    ]
    print(f"\ncompare with {old_path}")
    print(f"  rows found on one side only (rank or year differs): {len(only)}")
    if len(only):
        print(only[["year", "rank", "name_new", "name_new_old", "_merge"]].to_string(index=False))
    print(f"  rows with a different name_new or score: {len(changed)}")
    print("  expected: SSN 2017 (old name empty), JSS 2017 (now U-0222), College of Engineering Pune (C-41593)")
    if len(changed):
        print(changed[["year", "rank", "name_new_old", "name_new", "score_old", "score"]].to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="scraped CSV from step 1 (default: newest in interim/)")
    ap.add_argument("--compare", help="old my_clean.csv to diff against")
    args = ap.parse_args()

    CLEAN.mkdir(exist_ok=True)
    INTERIM.mkdir(exist_ok=True)
    path = Path(args.input) if args.input else latest(INTERIM, "nirf_overall_scraped_*.csv")
    df = pd.read_csv(path)
    print(f"read {len(df)} rows from {path}")

    df = build_ids(df)
    df = build_names(df)
    df = build_locations(df)

    problems = audit(df)
    if problems:
        print("\nAUDIT FAILED - nothing written:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("\naudit passed: every row has a valid id and a name, no id repeats within a year")

    ordered = df.sort_values(["year", "rank"], kind="stable")
    inst = (
        ordered.groupby("id_new", sort=False)
        .agg(name_new=("name_new", "last"), location_clean=("location_clean", "last"),
             first_year=("year", "min"), last_year=("year", "max"), n_years=("year", "nunique"))
        .reset_index()
    )
    inst["is_placeholder"] = inst["id_new"].str.startswith("X-")

    clean_cols = ["year", "id_new", "name_new", "location_raw", "location_clean",
                  "rank", "tlr", "rpc", "go", "oi", "pr"]
    df[clean_cols].to_csv(CLEAN / f"nirf_overall_clean_{TODAY}.csv", index=False)
    inst.to_csv(CLEAN / f"institutions_{TODAY}.csv", index=False)

    compat = df[["score", "rank", "year", "location_clean", "id_new", "name_new"]].rename(
        columns={"location_clean": "location"}
    )
    compat.to_csv(CLEAN / "my_clean_fixed.csv", index=False)
    pd.DataFrame(LOG).to_csv(INTERIM / f"cleaning_log_{TODAY}.csv", index=False)

    print(f"\n{len(inst)} institutions, {int(inst['is_placeholder'].sum())} of them 2017-only placeholders")
    print(f"written to {CLEAN}/ and {INTERIM}/cleaning_log_{TODAY}.csv")

    if args.compare:
        compare(compat, args.compare)


if __name__ == "__main__":
    main()
