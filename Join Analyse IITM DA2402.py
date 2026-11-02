#!/usr/bin/env python3
"""
Step 5 - join NIRF (step 2) with OpenAlex (step 4) and compute the first results.

Reads  (newest file matching, or pass --nirf / --yearly / --crosswalk):
    clean/nirf_overall_clean_<date>.csv
    interim/openalex_crosswalk_<date>.csv
    interim/openalex_yearly_<date>.csv
Writes:
    clean/nirf_openalex_joined_<date>.csv       one row per institution-year (the dashboard table)
    interim/spearman_by_year_<date>.csv         rank correlations, several specifications
    interim/biggest_disagreements_<date>.csv    largest rank gaps per year
    interim/join_log_<date>.csv                 counts for the cleaning log

Choices (all stated in the slides):
  * Window: NIRF year Y is compared with OpenAlex papers from Y-3 .. Y-1  (3 years,
    the window NIRF documents for universities/colleges; "Overall" has no stated window).
    Sensitivity: window shifted back one year (Y-4 .. Y-2).
  * Main count: works whose authors list the institution itself ("own").
    Sensitivity: "lineage" count (institution + units filed beneath it).
  * 2026 and later are never used (2026 is a partial year).
Only pandas and numpy are needed.
"""
import argparse, glob, os, sys, datetime as dt
import numpy as np
import pandas as pd

TODAY = dt.date.today().isoformat()
WINDOW_LEN = 3
LAST_FULL_YEAR = 2025
LINEAGE_FLAG = 1.05      # lineage count > 5% above own count
OA_FLAG = 1.15           # OpenAlex yearly count > 15% above works-filter count
AIIMS_DELHI_OA = "I63739035"   # looks like a merged all-AIIMS record
N_BOOT = 1000


def newest(pattern, explicit):
    if explicit:
        return explicit
    files = sorted(glob.glob(pattern))
    if not files:
        sys.exit(f"No file matches {pattern}. Pass the path with the matching option.")
    return files[-1]


def window_sums(yearly, Y, shift):
    lo, hi = Y - WINDOW_LEN - shift, Y - 1 - shift
    assert hi <= LAST_FULL_YEAR, f"window {lo}-{hi} reaches a partial year"
    sub = yearly[yearly.year.between(lo, hi)]
    g = sub.groupby("openalex_id").agg(
        pubs_own=("works_all_own", "sum"),
        pubs_lineage=("works_all_lineage", "sum"),
        pubs_article_lineage=("works_article_lineage", "sum"),
        cited1_lineage=("works_cited_ge1_lineage", "sum"),
        cited10_lineage=("works_cited_ge10_lineage", "sum"),
        oa_pubs_year=("oa_works_count_year", "sum"),
        cites_received=("oa_cited_by_count_year", "sum"),
        n_oa_years=("year", "nunique"),
        n_oa_missing=("oa_cited_by_count_year", lambda s: int(s.isna().sum())),
    )
    return g


def spearman(df, a, b):
    d = df[[a, b]].dropna()
    if len(d) < 5:
        return np.nan, len(d)
    return d[a].rank().corr(d[b].rank()), len(d)


def boot_ci(df, a, b, rng):
    d = df[[a, b]].dropna().reset_index(drop=True)
    n = len(d)
    if n < 10:
        return np.nan, np.nan
    vals = []
    for _ in range(N_BOOT):
        s = d.iloc[rng.integers(0, n, n)]
        r = s[a].rank().corr(s[b].rank())
        if not np.isnan(r):
            vals.append(r)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nirf"); ap.add_argument("--yearly"); ap.add_argument("--crosswalk")
    a = ap.parse_args()
    nirf_p = newest("clean/nirf_overall_clean_*.csv", a.nirf)
    year_p = newest("interim/openalex_yearly_*.csv", a.yearly)
    xw_p = newest("interim/openalex_crosswalk_*.csv", a.crosswalk)
    print("NIRF     :", nirf_p); print("YEARLY   :", year_p); print("CROSSWALK:", xw_p)

    nirf = pd.read_csv(nirf_p)
    yearly = pd.read_csv(year_p)
    xw = pd.read_csv(xw_p)
    log = []

    # ---- crosswalk checks ----
    assert xw.id_new.is_unique, "an id_new appears twice in the crosswalk"
    dup_oa = xw[xw.openalex_id.duplicated(keep=False)]
    if len(dup_oa):
        print("WARNING: two NIRF institutions share one OpenAlex id:\n", dup_oa.to_string())
    log.append(("crosswalk rows", len(xw), f"openalex ids shared by 2+ institutions: {dup_oa.openalex_id.nunique()}"))

    # ---- join NIRF to the crosswalk ----
    n0 = len(nirf)
    df = nirf.merge(xw[["id_new", "openalex_id", "ror_id", "decision"]], on="id_new", how="left", validate="m:1")
    assert len(df) == n0
    no_oa = df.openalex_id.isna().sum()
    log.append(("NIRF rows without an OpenAlex id", int(no_oa), "should be 0"))

    # ---- window sums, main and shifted ----
    parts = []
    for Y, g in df.groupby("year"):
        main_w = window_sums(yearly, Y, 0)
        sh = window_sums(yearly, Y, 1)[["pubs_own", "cites_received"]].add_suffix("_shift1")
        w = main_w.join(sh, how="left")
        w["year"] = Y
        w["win_from"], w["win_to"] = Y - WINDOW_LEN, Y - 1
        parts.append(w.reset_index())
    wins = pd.concat(parts, ignore_index=True)
    df = df.merge(wins, on=["year", "openalex_id"], how="left", validate="1:1")
    miss = df.pubs_own.isna().sum()
    log.append(("NIRF rows with no OpenAlex window counts", int(miss), "should be 0"))
    log.append(("rows with any missing citation value inside window", int((df.n_oa_missing > 0).sum()), "should be 0"))
    short = df[df.n_oa_years < WINDOW_LEN]
    log.append(("rows whose window has fewer than 3 years of data", len(short), "should be 0"))

    # ---- derived columns and flags ----
    df["pubs_per_year"] = df.pubs_own / WINDOW_LEN
    df["share_ge10_lineage"] = df.cited10_lineage / df.pubs_lineage.replace(0, np.nan)
    df["lineage_ratio"] = df.pubs_lineage / df.pubs_own.replace(0, np.nan)
    df["oa_ratio"] = df.oa_pubs_year / df.pubs_own.replace(0, np.nan)
    df["flag_lineage_inflated"] = df.lineage_ratio > LINEAGE_FLAG
    df["flag_oa_disagree"] = df.oa_ratio > OA_FLAG
    df["flag_aiims_merged"] = df.openalex_id == AIIMS_DELHI_OA
    df["flag_any"] = df[["flag_lineage_inflated", "flag_oa_disagree", "flag_aiims_merged"]].any(axis=1)
    for c in ["flag_lineage_inflated", "flag_oa_disagree", "flag_aiims_merged", "flag_any"]:
        log.append((c, int(df[c].sum()), "institution-years"))

    # within-year ranks (1 = highest) so the dashboard can show rank vs rank
    for col in ["rpc", "pubs_own", "cites_received"]:
        df[f"rank_{col}"] = df.groupby("year")[col].rank(ascending=False, method="min")
    df["rank_gap_pubs_vs_rpc"] = df.rank_pubs_own - df.rank_rpc   # + : publishes less than its research score suggests
    df["rank_gap_cites_vs_rpc"] = df.rank_cites_received - df.rank_rpc

    # ---- Spearman table ----
    rng = np.random.default_rng(42)
    rows = []

    def add(year, spec, sub, x, y_, ci=False):
        r, n = spearman(sub, x, y_)
        lo, hi = boot_ci(sub, x, y_, rng) if ci else (np.nan, np.nan)
        rows.append(dict(year=year, spec=spec, metric=y_, n=n, spearman=r, ci_low=lo, ci_high=hi))

    for Y, g in df.groupby("year"):
        for m in ["pubs_own", "cites_received"]:
            add(Y, "main", g, "rpc", m, ci=True)
            add(Y, "excl_flagged", g[~g.flag_any], "rpc", m)
            add(Y, "top50_only", g[g["rank"] <= 50], "rpc", m)
            add(Y, "rank_51_100", g[g["rank"] > 50], "rpc", m)
            add(Y, "shifted_window", g, "rpc", m + "_shift1")
        add(Y, "lineage", g, "rpc", "pubs_lineage")
        add(Y, "lineage", g, "rpc", "share_ge10_lineage")
        # control: does NIRF *overall rank* track papers too? (rank is 1=best, so flip sign)
        add(Y, "overall_rank_control", g.assign(neg_rank=-g["rank"]), "neg_rank", "pubs_own")
    sp = pd.DataFrame(rows)

    # ---- biggest disagreements ----
    dis = (df.assign(abs_gap=df.rank_gap_pubs_vs_rpc.abs())
             .sort_values(["year", "abs_gap"], ascending=[True, False])
             .groupby("year").head(10)
             [["year", "id_new", "name_new", "rank", "rpc", "pubs_own", "rank_rpc", "rank_pubs_own",
               "rank_gap_pubs_vs_rpc", "flag_any"]])

    # ---- write ----
    os.makedirs("clean", exist_ok=True); os.makedirs("interim", exist_ok=True)
    out_join = f"clean/nirf_openalex_joined_{TODAY}.csv"
    out_sp = f"interim/spearman_by_year_{TODAY}.csv"
    out_dis = f"interim/biggest_disagreements_{TODAY}.csv"
    out_log = f"interim/join_log_{TODAY}.csv"
    df.to_csv(out_join, index=False)
    sp.to_csv(out_sp, index=False)
    dis.to_csv(out_dis, index=False)
    pd.DataFrame(log, columns=["step", "count", "detail"]).to_csv(out_log, index=False)

    # ---- print what to check ----
    pd.set_option("display.width", 200)
    print("\nJOIN LOG"); print(pd.DataFrame(log, columns=["step", "count", "detail"]).to_string(index=False))
    print("\nSPEARMAN, NIRF research score (RPC) vs OpenAlex, by year (main specification)")
    mn = sp[sp.spec == "main"].pivot(index="year", columns="metric", values="spearman").round(2)
    print(mn.to_string())
    print("\nSame, by specification (pubs_own only)")
    t = sp[(sp.metric == "pubs_own") | (sp.metric == "pubs_lineage")]
    print(t.pivot_table(index="year", columns="spec", values="spearman").round(2).to_string())
    print(f"\nWrote:\n  {out_join}\n  {out_sp}\n  {out_dis}\n  {out_log}")


if __name__ == "__main__":
    main()
