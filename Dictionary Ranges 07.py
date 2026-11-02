#!/usr/bin/env python3
"""
Step 7 - add an allowed_range column (and the range actually seen) to clean/data_dictionary.csv.
The rubric asks the dictionary to list column, dtype, unit, source and allowed range.
Run from the project folder after step 6:  python 07_dictionary_ranges.py
It also checks that every value sits inside its allowed range and prints any column that does not.
"""
import glob
import pandas as pd

RULES = {   # column -> (low, high) allowed, or a text rule
    "year": (2017, 2025), "rank": (1, 100), "tlr": (0, 100), "rpc": (0, 100), "go": (0, 100), "oi": (0, 100), "pr": (0, 100),
    "pubs_own": (0, None), "pubs_lineage": (0, None), "pubs_article_lineage": (0, None), "cited1_lineage": (0, None),
    "cited10_lineage": (0, None), "oa_pubs_year": (0, None), "cites_received": (0, None), "n_oa_years": (3, 3), "n_oa_missing": (0, 0),
    "win_from": (2014, 2022), "win_to": (2016, 2024), "pubs_own_shift1": (0, None), "cites_received_shift1": (0, None),
    "pubs_per_year": (0, None), "share_ge10_lineage": (0, 1), "lineage_ratio": (1, None), "oa_ratio": (0, None),
    "rank_rpc": (1, 101), "rank_pubs_own": (1, 101), "rank_cites_received": (1, 101),   # 2020 lists 101 institutions
    "rank_gap_pubs_vs_rpc": (-100, 100), "rank_gap_cites_vs_rpc": (-100, 100),
}
TEXT = {"id_new": "non-empty; U-, C-, I-, X- followed by digits", "name_new": "non-empty lower-case text", "location_raw": "non-empty text",
        "location_clean": "non-empty text", "openalex_id": "OpenAlex id: I followed by digits", "ror_id": "URL starting https://ror.org/",
        "decision": "auto or manual"}
BOOL = {"flag_lineage_inflated", "flag_oa_disagree", "flag_aiims_merged", "flag_any"}

j = pd.read_csv(sorted(glob.glob("clean/nirf_openalex_joined_*.csv"))[-1])
d = pd.read_csv("clean/data_dictionary.csv")
allowed, seen, bad = [], [], []
for c in d.column:
    s = j[c]
    if c in TEXT:
        allowed.append(TEXT[c]); seen.append(f"{s.nunique()} distinct values")
    elif c in BOOL:
        allowed.append("True or False"); seen.append(", ".join(sorted(map(str, s.unique()))))
    else:
        lo, hi = RULES[c]
        allowed.append(f"{lo} to {hi if hi is not None else 'no upper limit'}")
        seen.append(f"{s.min():g} to {s.max():g}")
        if s.min() < lo or (hi is not None and s.max() > hi):
            bad.append((c, s.min(), s.max(), lo, hi))
d["allowed_range"] = allowed
d["observed_range"] = seen
d.to_csv("clean/data_dictionary.csv", index=False)
print("data dictionary now has allowed_range and observed_range for", len(d), "columns")
print("columns outside their allowed range:", bad if bad else "none")
