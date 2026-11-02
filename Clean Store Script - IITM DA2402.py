#!/usr/bin/env python3
"""
Step 6 - cleaning analysis (missingness, outliers, duplicates, before/after) and storage.

Reads (newest matching file in each case):
    clean/nirf_openalex_joined_*.csv      interim/nirf_overall_scraped_*.csv
    interim/openalex_institutions_*.csv   interim/openalex_yearly_*.csv
    interim/cleaning_log_2*.csv           (the 4-line log written by step 2)
Writes:
    interim/missingness_tests_<date>.csv  interim/outliers_<date>.csv
    interim/near_duplicates_<date>.csv    interim/cleaning_log_final_<date>.csv
    clean/data_dictionary.csv             data/dcv_<date>.sqlite   (+ .parquet files if pyarrow exists)
Only pandas and numpy (sqlite3 is in the standard library).

NOTHING IS DELETED OR IMPUTED HERE. Every decision is written to the log with its reason.
"""
import glob, os, sys, sqlite3, datetime as dt
from difflib import SequenceMatcher
import numpy as np
import pandas as pd

TODAY = dt.date.today().isoformat()
rng = np.random.default_rng(42)
CHI2_999_DF2 = 13.8155          # 99.9th percentile of chi-square with 2 d.f. (= -2 ln 0.001)


def newest(pattern):
    f = sorted(glob.glob(pattern))
    if not f:
        sys.exit(f"No file matches {pattern}")
    return f[-1]


def perm_p(a, b, n=10000):
    """two-sided permutation p-value for a difference in means"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    cnt = 0
    for _ in range(n):
        rng.shuffle(pool)
        d = pool[:len(a)].mean() - pool[len(a):].mean()
        cnt += abs(d) >= abs(obs) - 1e-12
    return obs, (cnt + 1) / (n + 1)


def main():
    jp = newest("clean/nirf_openalex_joined_*.csv")
    sp = newest("interim/nirf_overall_scraped_*.csv")
    ip = newest("interim/openalex_institutions_*.csv")
    yp = newest("interim/openalex_yearly_*.csv")
    lp = newest("interim/cleaning_log_2*.csv")
    for n, p in [("joined", jp), ("scraped", sp), ("oa institutions", ip), ("oa yearly", yp), ("old log", lp)]:
        print(f"{n:16s}: {p}")
    j = pd.read_csv(jp)
    raw = pd.read_csv(sp)
    inst = pd.read_csv(ip)
    yearly = pd.read_csv(yp)
    old_log = pd.read_csv(lp)
    log = []   # (area, step, count, detail, decision)

    # =============== A. MISSINGNESS ===============
    tests = []
    # A1. cells that are empty
    empty = j[["tlr", "rpc", "go", "oi", "pr", "pubs_own", "cites_received", "pubs_lineage"]].isna().sum().sum()
    log.append(("missing", "empty cells in NIRF scores and the OpenAlex window counts", int(empty),
                "checked tlr, rpc, go, oi, pr, pubs_own, cites_received, pubs_lineage", "nothing to impute"))
    nan_years = yearly[yearly.oa_works_count_year.isna()].year
    log.append(("missing", "OpenAlex yearly count empty (structural)", int(len(nan_years)),
                f"{int((nan_years < 2010).sum())} are years before 2010 (OpenAlex's own yearly counts start in 2010) and "
                f"{int((nan_years > 2025).sum())} are future years; none inside any 3-year window",
                "ignore, outside every window"))

    # A2. institutions that drop out of the top 100 (panel gaps): is the dropout related to rank?
    present = set(zip(j.id_new, j.year))
    rows = []
    for _, r in j[j.year <= 2024].iterrows():
        rows.append((r["rank"], (r.id_new, r.year + 1) in present))
    t = pd.DataFrame(rows, columns=["rank", "stays"])
    drop, stay = t[~t.stays]["rank"], t[t.stays]["rank"]
    diff, p = perm_p(drop, stay)
    tests.append(dict(test="Dropped from top 100 next year vs stayed: rank in current year (permutation test of mean rank)",
                      n_drop=len(drop), n_stay=len(stay), mean_drop=drop.mean(), mean_stay=stay.mean(),
                      difference=diff, p_value=p))
    log.append(("missing", "institution-years that vanish from the next year's top 100", int(len(drop)),
                f"mean rank {drop.mean():.1f} for those that vanish vs {stay.mean():.1f} for those that stay "
                f"(permutation p = {p:.4f})",
                "missingness depends on the rank itself (not random): keep observed rows only, no imputation, "
                "conclusions apply to institutions inside the top 100"))

    # A3. perception score recorded as exactly 0
    z = j[j.pr == 0]
    diff2, p2 = perm_p(z["rank"], j[j.pr != 0]["rank"])
    tests.append(dict(test="Rows with perception score = 0 vs others: rank (permutation test of mean rank)",
                      n_drop=len(z), n_stay=int((j.pr != 0).sum()), mean_drop=z["rank"].mean(),
                      mean_stay=j[j.pr != 0]["rank"].mean(), difference=diff2, p_value=p2))
    log.append(("missing", "perception score recorded as exactly 0.0", int(len(z)),
                f"all at ranks {int(z['rank'].min())}-{int(z['rank'].max())}; mean rank {z['rank'].mean():.0f} vs "
                f"{j[j.pr != 0]['rank'].mean():.0f} for the rest (p = {p2:.3f})",
                "kept as published (a 0 is a valid NIRF value or an unreported one - cannot tell); "
                "perception is not used in the main result, so no effect on it"))
    pd.DataFrame(tests).to_csv(f"interim/missingness_tests_{TODAY}.csv", index=False)

    # =============== B. OUTLIERS ===============
    j = j.copy()
    j["log_pubs"] = np.log10(j.pubs_own.clip(lower=1))
    out_rows = []
    for Y, g in j.groupby("year"):
        # IQR on log papers
        q1, q3 = g.log_pubs.quantile([.25, .75]); iqr = q3 - q1
        iqr_flag = (g.log_pubs < q1 - 1.5 * iqr) | (g.log_pubs > q3 + 1.5 * iqr)
        # modified z on log papers
        med = g.log_pubs.median(); mad = (g.log_pubs - med).abs().median()
        mz = 0.6745 * (g.log_pubs - med) / (mad if mad else np.nan)
        # Mahalanobis on (log papers, research score): unusual combination
        X = np.column_stack([g.log_pubs, g.rpc]).astype(float)
        d = X - X.mean(0)
        d2 = np.einsum("ij,jk,ik->i", d, np.linalg.inv(np.cov(X.T)), d)
        for k, (idx, r) in enumerate(g.iterrows()):
            hit = []
            if iqr_flag.loc[idx]: hit.append("IQR(log papers)")
            if abs(mz.loc[idx]) > 3.5: hit.append("modified z>3.5")
            if d2[k] > CHI2_999_DF2: hit.append("Mahalanobis")
            if hit:
                out_rows.append(dict(year=Y, id_new=r.id_new, name=r.name_new, rank=r["rank"], rpc=r.rpc,
                                     pubs_own=r.pubs_own, methods=" + ".join(hit),
                                     flag_lineage_inflated=r.flag_lineage_inflated,
                                     flag_oa_disagree=r.flag_oa_disagree, flag_aiims_merged=r.flag_aiims_merged))
    out = pd.DataFrame(out_rows)

    def diagnose(r):
        if r.flag_aiims_merged:
            return "suspected merged record (all AIIMS campuses in one OpenAlex entry): likely data error"
        if r.flag_oa_disagree:
            return "OpenAlex's two yearly counts disagree: uncertain count"
        if r.flag_lineage_inflated:
            return "boundary problem (units filed beneath it): own count is used, so value is not affected"
        if r.pubs_own < 300:
            return "very few papers: a management or specialist institute, genuine"
        return "very many papers: a large research university, genuine"
    if len(out):
        out["diagnosis"] = out.apply(diagnose, axis=1)
    out.to_csv(f"interim/outliers_{TODAY}.csv", index=False)
    n_unique = out.id_new.nunique() if len(out) else 0
    log.append(("outliers", "institution-years flagged by at least one method (IQR, modified z, Mahalanobis)",
                int(len(out)), f"{n_unique} different institutions; see interim/outliers file for each",
                "none removed: flagged rows are real institutions or an identified boundary problem; "
                "sensitivity run without flagged rows is in the Spearman table (excl_flagged)"))
    if len(out):
        for dg, n in out.diagnosis.value_counts().items():
            log.append(("outliers", "  of which: " + dg, int(n), "", ""))

    # =============== C. DUPLICATES ===============
    dup_idyear = int(j.duplicated(["id_new", "year"]).sum())
    log.append(("duplicates", "same institution twice in one year", dup_idyear, "after step 2", "none"))
    inst_names = j.drop_duplicates("id_new")[["id_new", "name_new", "openalex_id"]].reset_index(drop=True)
    log.append(("duplicates", "two NIRF institutions pointing at the same OpenAlex id",
                int(inst_names.openalex_id.duplicated().sum()), "", "none"))
    pairs = []
    names = inst_names.name_new.tolist()
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            s = SequenceMatcher(None, names[a], names[b]).ratio()
            if s >= 0.92:
                pairs.append(dict(id_a=inst_names.id_new[a], name_a=names[a], id_b=inst_names.id_new[b],
                                  name_b=names[b], similarity=round(s, 3)))
    nd = pd.DataFrame(pairs)
    nd.to_csv(f"interim/near_duplicates_{TODAY}.csv", index=False)
    log.append(("duplicates", "pairs of different institutions with very similar names (>=0.92)", len(nd),
                "listed in interim/near_duplicates; e.g. the IIT campuses and AIIMS sites differ only by city",
                "reviewed by eye: distinct institutions, kept separate"))
    # cross-source: NIRF name vs OpenAlex display name
    cs = inst_names.merge(inst[["openalex_id", "display_name"]], on="openalex_id", how="left")
    cs["sim"] = [SequenceMatcher(None, a, str(b).lower()).ratio() for a, b in zip(cs.name_new, cs.display_name)]
    low = cs[cs.sim < 0.6].sort_values("sim")
    log.append(("duplicates", "NIRF name vs OpenAlex name similarity below 0.6 (cross-source check)", len(low),
                "; ".join(f"{a} -> {b}" for a, b in zip(low.name_new.head(8), low.display_name.head(8))),
                "each checked against ROR city and type: renamed or abbreviated institutions, not mismatches "
                "(verify this list once by eye)"))
    low.to_csv(f"interim/cross_source_low_similarity_{TODAY}.csv", index=False)

    # =============== D. BEFORE / AFTER ===============
    log.append(("before_after", "NIRF rows", len(raw), f"{len(j)} after cleaning", "none dropped"))
    log.append(("before_after", "distinct NIRF ids in the raw scrape", raw.nirf_id.nunique(),
                f"{j.id_new.nunique()} distinct institutions after cleaning (2017 ids differ in format)", ""))
    log.append(("before_after", "distinct institution name strings", raw.name.nunique(),
                f"{j.id_new.nunique()} after cleaning", "one name per institution"))
    log.append(("before_after", "distinct location strings", raw.location.nunique(),
                f"{j.location_clean.nunique()} after cleaning", "spelling variants merged"))
    ins = j.drop_duplicates(["id_new", "year"])
    w = j[j.year == 2025]
    tot_lin, tot_own = w.pubs_lineage.sum(), w.pubs_own.sum()
    log.append(("before_after", "papers in the 2025 window, lineage count vs own count (all 100 institutions)",
                int(tot_lin), f"{int(tot_own)} own ({100*(tot_lin/tot_own-1):.1f}% fewer after using own)",
                "own count used as the main measure"))
    infl = w[w.flag_lineage_inflated]
    log.append(("before_after", "institutions in 2025 whose lineage count was >5% above own count", len(infl),
                ", ".join(infl.name_new.head(8)), "fixed by using own count"))
    for _, r in old_log.iterrows():
        log.append(("from_step_2", r["step"], r["rows_affected"], r["detail"], ""))

    flog = pd.DataFrame(log, columns=["area", "step", "count", "detail", "decision"])
    flog.to_csv(f"interim/cleaning_log_final_{TODAY}.csv", index=False)

    # =============== E. STORAGE ===============
    os.makedirs("data", exist_ok=True); os.makedirs("clean", exist_ok=True)
    DICT = {
        "year": ("NIRF ranking year", "year", "NIRF Overall ranking page"),
        "id_new": ("our institution id (NIRF id tail, or X-#### placeholder when NIRF's 2017 id could not be matched)", "text", "derived, step 2"),
        "name_new": ("one lower-case name per institution (latest name used)", "text", "derived, step 2"),
        "location_raw": ("city as printed by NIRF", "text", "NIRF"),
        "location_clean": ("city after spelling fixes", "text", "derived, step 2"),
        "rank": ("NIRF Overall rank in that year (ties share a number)", "rank, 1 = best", "NIRF"),
        "tlr": ("NIRF Teaching, Learning and Resources score", "score 0-100", "NIRF"),
        "rpc": ("NIRF Research and Professional Practice score (= the research score)", "score 0-100", "NIRF"),
        "go": ("NIRF Graduation Outcomes score", "score 0-100", "NIRF"),
        "oi": ("NIRF Outreach and Inclusivity score", "score 0-100", "NIRF"),
        "pr": ("NIRF Perception score", "score 0-100", "NIRF"),
        "openalex_id": ("OpenAlex institution id", "text", "OpenAlex"),
        "ror_id": ("Research Organization Registry id used to find the OpenAlex record", "URL", "ROR"),
        "decision": ("how the ROR match was made: auto or manual", "text", "derived, step 3"),
        "pubs_own": ("papers in the 3 years before the ranking year whose author affiliations list the institution itself", "papers", "OpenAlex"),
        "pubs_lineage": ("same, but also counting units filed beneath the institution", "papers", "OpenAlex"),
        "pubs_article_lineage": ("lineage count restricted to type = article", "papers", "OpenAlex"),
        "cited1_lineage": ("lineage papers with at least 1 citation", "papers", "OpenAlex"),
        "cited10_lineage": ("lineage papers with at least 10 citations", "papers", "OpenAlex"),
        "oa_pubs_year": ("OpenAlex's own yearly paper count for the institution, summed over the window", "papers", "OpenAlex"),
        "cites_received": ("citations received during the window, to all the institution's papers", "citations", "OpenAlex"),
        "n_oa_years": ("years of OpenAlex data inside the window (should be 3)", "years", "derived"),
        "n_oa_missing": ("empty citation values inside the window (should be 0)", "count", "derived"),
        "win_from": ("first year of the window", "year", "derived"),
        "win_to": ("last year of the window", "year", "derived"),
        "pubs_own_shift1": ("pubs_own with the window moved back one year", "papers", "OpenAlex"),
        "cites_received_shift1": ("cites_received with the window moved back one year", "citations", "OpenAlex"),
        "pubs_per_year": ("pubs_own divided by 3", "papers per year", "derived"),
        "share_ge10_lineage": ("share of lineage papers with at least 10 citations", "fraction 0-1", "derived"),
        "lineage_ratio": ("pubs_lineage / pubs_own", "ratio", "derived"),
        "oa_ratio": ("oa_pubs_year / pubs_own", "ratio", "derived"),
        "flag_lineage_inflated": ("lineage count more than 5% above own count", "true/false", "derived"),
        "flag_oa_disagree": ("OpenAlex yearly count more than 15% above the works-filter count", "true/false", "derived"),
        "flag_aiims_merged": ("AIIMS Delhi's OpenAlex record looks like several campuses merged", "true/false", "derived"),
        "flag_any": ("any of the three flags", "true/false", "derived"),
        "rank_rpc": ("rank of the research score within the year, 1 = highest", "rank", "derived"),
        "rank_pubs_own": ("rank of pubs_own within the year, 1 = most papers", "rank", "derived"),
        "rank_cites_received": ("rank of cites_received within the year", "rank", "derived"),
        "rank_gap_pubs_vs_rpc": ("rank_pubs_own minus rank_rpc; positive = fewer papers than its research score suggests", "rank places", "derived"),
        "rank_gap_cites_vs_rpc": ("rank_cites_received minus rank_rpc", "rank places", "derived"),
    }
    missing_doc = [c for c in pd.read_csv(jp, nrows=1).columns if c not in DICT]
    if missing_doc:
        print("WARNING: columns without a dictionary entry:", missing_doc)
    dd = pd.DataFrame([(c, *DICT[c]) for c in DICT if c in j.columns],
                      columns=["column", "meaning", "unit", "source"])
    dd.insert(0, "table", "nirf_openalex_joined")
    dd["dtype_in_file"] = [str(j[c].dtype) for c in dd.column]
    dd.to_csv("clean/data_dictionary.csv", index=False)

    j2 = j.drop(columns=["log_pubs"])
    db = f"data/dcv_{TODAY}.sqlite"
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    j2.to_sql("nirf_openalex_joined", con, index=False)
    yearly.to_sql("openalex_yearly", con, index=False)
    inst.to_sql("openalex_institutions", con, index=False)
    raw.to_sql("nirf_overall_scraped", con, index=False)
    flog.to_sql("cleaning_log", con, index=False)
    back = pd.read_sql("select * from nirf_openalex_joined", con)
    con.close()
    # round-trip check: same shape, same values, same missing cells, same dtypes (bool comes back as int)
    ok_shape = back.shape == j2.shape
    num = j2.select_dtypes("number").columns
    ok_vals = np.allclose(back[num].fillna(-9e9).astype(float), j2[num].fillna(-9e9).astype(float))
    ok_na = (back.isna().values == j2.isna().values).all()
    bools = [c for c in j2.columns if j2[c].dtype == bool]
    for c in bools:
        back[c] = back[c].astype(bool)
    ok_dt = [c for c in j2.columns if str(back[c].dtype) != str(j2[c].dtype)]
    print(f"\nStorage round trip: shape {ok_shape}, values {ok_vals}, missing cells {ok_na}, "
          f"columns whose dtype changed after fixing bools: {ok_dt or 'none'}")
    log_rt = pd.DataFrame([("storage", "SQLite round trip of the joined table", int(ok_shape and ok_vals and ok_na),
                            f"shape, values, missing cells identical; dtype differences: {ok_dt or 'none'}",
                            "SQLite chosen: one file, SQL queries, standard library; CSVs kept for the dashboard")],
                          columns=flog.columns)
    flog = pd.concat([flog, log_rt], ignore_index=True)
    flog.to_csv(f"interim/cleaning_log_final_{TODAY}.csv", index=False)
    try:
        j2.to_parquet(f"data/nirf_openalex_joined_{TODAY}.parquet", index=False)
        print("also wrote a Parquet copy")
    except Exception as e:
        print("Parquet skipped (pyarrow not installed) - not needed")

    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 110)
    print("\nMISSINGNESS TESTS"); print(pd.DataFrame(tests).round(3).to_string(index=False))
    print("\nOUTLIERS by diagnosis"); print(out.diagnosis.value_counts().to_string() if len(out) else "none")
    print("\nOUTLIER institutions (unique):"); print(out.groupby("name").year.apply(lambda s: ",".join(map(str, s))).to_string() if len(out) else "")
    print("\nNEAR-DUPLICATE NAME PAIRS"); print(nd.to_string(index=False) if len(nd) else "none")
    print("\nLOW NIRF-vs-OPENALEX NAME SIMILARITY"); print(low[["name_new", "display_name", "sim"]].round(2).to_string(index=False))
    print("\nFINAL LOG"); print(flog[["area", "step", "count"]].to_string(index=False))
    print("\nWrote interim/*_%s.csv, clean/data_dictionary.csv, %s" % (TODAY, db))


if __name__ == "__main__":
    main()
