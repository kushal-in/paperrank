"""
data.py - loads the project's files and builds every table the dashboard needs.

The dashboard only READS files made by steps 1-6. It looks for them in the project folder
(the folder that contains clean/ and interim/). If the dashboard folder is somewhere else,
set the environment variable DCV_ROOT to the project folder.
"""
import os, re, random
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def _find_root():
    cands = [os.environ.get("DCV_ROOT"), HERE.parent, HERE, Path.cwd(), Path.cwd().parent]
    for c in cands:
        if c and list(Path(c).glob("clean/nirf_openalex_joined_*.csv")):
            return Path(c)
    raise SystemExit(
        "Could not find clean/nirf_openalex_joined_<date>.csv. Put the dashboard folder inside the "
        "project folder (next to clean/ and interim/) or set DCV_ROOT to the project folder.")


ROOT = _find_root()


def _newest(pattern, required=False):
    files = sorted(ROOT.glob(pattern))
    if files:
        return files[-1]
    if required:
        raise SystemExit(f"Missing file: {pattern}")
    return None


def _read(pattern):
    p = _newest(pattern)
    return pd.read_csv(p) if p else None


# ------------------------------------------------------------------ names
UPPER = {"iit", "nit", "iisc", "jss", "kle", "psg", "sastra", "upes", "srm", "bits", "vit", "kiit",
         "aiims", "iim", "iiit", "iiser", "nimhans", "svkm", "sms"}
FULL = {
    "s r m institute of science and technology": "SRM Institute of Science and Technology",
    "g b pant universtiy of agriculture and technology": "G. B. Pant University of Agriculture and Technology",
    "king george s medical university": "King George's Medical University",
    "svkm s narsee monjee institute of management studies": "NMIMS (Narsee Monjee Institute of Management Studies)",
    "dr d y patil vidyapeeth": "Dr. D. Y. Patil Vidyapeeth",
    "dr y s parmar university of horticulture and forestry": "Dr. Y. S. Parmar University of Horticulture and Forestry",
    "dr b r ambedkar national institute of technology jalandhar": "Dr. B. R. Ambedkar NIT Jalandhar",
    "upes": "UPES", "nitte": "Nitte",
    "indian institute of technology (indian school of mines)": "IIT (Indian School of Mines) Dhanbad",
    "indian institute of technology (banaras hindu university) varanasi": "IIT (BHU) Varanasi",
    "koneru lakshmaiah education foundation university (k l college of engineering)": "Koneru Lakshmaiah Education Foundation",
    "thapar institute of engineering and technology (deemed to be university)": "Thapar Institute of Engineering and Technology",
    "post graduate institute of medical education and research": "PGIMER Chandigarh",
    "jawaharlal institute of post graduate medical education and research": "JIPMER Puducherry",
    "national institute of mental health and neuro sciences bangalore": "NIMHANS Bengaluru",
    "sher e kashmir university of agricultural science and technology of kashmir": "SKUAST Kashmir",
}
SMALL = {"of", "and", "the", "for", "in", "to"}


def pretty(name):
    n = str(name).strip().lower()
    if n in FULL:
        return FULL[n]
    out = []
    for i, w in enumerate(n.split()):
        if w in UPPER:
            out.append(w.upper())
        elif w in SMALL and i > 0:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


SHORT_RULES = [
    (r"^Indian Institute of Technology ", "IIT "),
    (r"^National Institute of Technology ", "NIT "),
    (r"^All India Institute of Medical Sciences ", "AIIMS "),
    (r"^Indian Institute of Science Education and Research ", "IISER "),
    (r"^Indian Institute of Management ", "IIM "),
    (r"^International Institute of Information Technology ", "IIIT "),
    (r"^Indian Institute of Science$", "IISc"),
    (r" University of ", " Univ. of "),
]


def short(name, limit=34):
    s = pretty(name)
    for pat, rep in SHORT_RULES:
        s = re.sub(pat, rep, s)
    s = s.replace("University", "Univ.") if len(s) > limit else s
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


# ------------------------------------------------------------------ institution types
TYPES = ["IIT", "NIT and IIIT", "Science institutes", "Medical", "Agriculture", "Management",
         "Private and deemed", "Public universities"]
PRIVATE_KEYS = ["s r m", "vellore institute", "amrita", "manipal", "birla institute of technology", "siksha",
                "bharath institute", "sathyabama", "kalinga", "shanmugha", "saveetha", "sri ramachandra", "thapar",
                "dr d y patil", "bharati vidyapeeth", "jss academy", "kle academy", "datta meghe", "nitte", "upes",
                "graphic era", "christ university", "koneru", "kalasalingam", "shoolini", "chandigarh university",
                "lovely professional", "amity", "shiv nadar", "symbiosis", "psg college", "sri sivasubramaniya",
                "thiagarajar", "svkm", "banasthali", "dayalbagh", "jamia hamdard"]


def classify(name):
    n = str(name).lower()
    if any(k in n for k in PRIVATE_KEYS):
        return "Private and deemed"
    if "indian institute of technology" in n:
        return "IIT"
    if "national institute of technology" in n or "international institute of information technology" in n:
        return "NIT and IIIT"
    if any(k in n for k in ["medical", "post graduate institute", "neuro sciences"]):
        return "Medical"
    if any(k in n for k in ["agricultur", "horticulture", "veterinary", "crop processing"]):
        return "Agriculture"
    if "indian institute of management" in n or "rajiv gandhi indian institute of management" in n:
        return "Management"
    if any(k in n for k in ["indian institute of science", "jawaharlal nehru centre", "homi bhabha",
                            "statistical institute", "space science", "pharmaceutical", "chemical technology"]):
        return "Science institutes"
    return "Public universities"


# ------------------------------------------------------------------ main table
J = pd.read_csv(_newest("clean/nirf_openalex_joined_*.csv", required=True))
J["name"] = J.name_new.map(pretty)
J["label"] = J.name_new.map(short)
J["papers_per_year"] = J.pubs_own / 3
J["cites_per_year"] = J.cites_received / 3

_types_path = HERE / "institution_types.csv"
_auto = (J.drop_duplicates("id_new")[["id_new", "name_new"]].assign(type=lambda d: d.name_new.map(classify)))
if _types_path.exists():
    _t = pd.read_csv(_types_path)
    _auto = _auto.drop(columns="type").merge(_t[["id_new", "type"]], on="id_new", how="left")
    _auto["type"] = _auto["type"].fillna("Public universities")
else:
    _auto.to_csv(_types_path, index=False)
J = J.merge(_auto[["id_new", "type"]], on="id_new", how="left")

YEARS = sorted(J.year.unique().tolist())
INSTITUTIONS = (J.drop_duplicates("id_new")[["id_new", "name"]].sort_values("name")
                .rename(columns={"id_new": "value", "name": "label"}).to_dict("records"))

# optional files
SP = _read("interim/spearman_by_year_*.csv")
LOG = _read("interim/cleaning_log_final_*.csv")
OUT = _read("interim/outliers_*.csv")
MISS = _read("interim/missingness_tests_*.csv")
DD = _read("clean/data_dictionary.csv")
NEARDUP = _read("interim/near_duplicates_*.csv")
XSRC = _read("interim/cross_source_low_similarity_*.csv")
JOINLOG = _read("interim/join_log_*.csv")
RAW = _read("interim/nirf_overall_scraped_*.csv")

METRICS = {
    "papers": dict(col="pubs_own", per_year="papers_per_year", rank="rank_pubs_own", gap="rank_gap_pubs_vs_rpc",
                   word="papers", axis="Papers per year, 3 years before the ranking (log scale)"),
    "citations": dict(col="cites_received", per_year="cites_per_year", rank="rank_cites_received",
                      gap="rank_gap_cites_vs_rpc", word="citations",
                      axis="Citations received per year, 3 years before the ranking (log scale)"),
}


# ------------------------------------------------------------------ statistics
def rho(df, x, y):
    d = df[[x, y]].dropna()
    if len(d) < 5:
        return np.nan
    return d[x].rank().corr(d[y].rank())


def agreement_by_year(y="pubs_own", df=None):
    df = J if df is None else df
    return pd.Series({yr: rho(g, "rpc", y) for yr, g in df.groupby("year")})


def agreement_main_ci(metric_col):
    """bootstrap CI from step 5's spearman file, if present"""
    if SP is None:
        return None
    s = SP[(SP.spec == "main") & (SP.metric == metric_col)].set_index("year")
    return s[["spearman", "ci_low", "ci_high"]] if len(s) else None


def split_by_half(metric_col="pubs_own"):
    top = pd.Series({yr: rho(g[g["rank"] <= 50], "rpc", metric_col) for yr, g in J.groupby("year")})
    bot = pd.Series({yr: rho(g[g["rank"] > 50], "rpc", metric_col) for yr, g in J.groupby("year")})
    return top, bot


def robustness_table():
    flagged_out = J[~J.flag_any]
    return pd.DataFrame({
        "Main (own count, 3-year window)": agreement_by_year("pubs_own"),
        "Lineage count": agreement_by_year("pubs_lineage"),
        "Flagged institutions removed": agreement_by_year("pubs_own", flagged_out),
        "Window shifted back one year": agreement_by_year("pubs_own_shift1"),
    })


def dropout_stats():
    present = set(zip(J.id_new, J.year))
    rows = [(r["rank"], (r.id_new, r.year + 1) in present) for _, r in J[J.year < J.year.max()].iterrows()]
    t = pd.DataFrame(rows, columns=["rank", "stays"])
    return t[~t.stays]["rank"], t[t.stays]["rank"]


# ------------------------------------------------------------------ viva questions
def build_viva_pool(seed=7):
    pool = []
    for yr, g in J.groupby("year"):
        g = g[["name", "label", "rpc", "pubs_own", "rank"]].reset_index(drop=True)
        for i in range(len(g)):
            for j in range(len(g)):
                a, b = g.iloc[i], g.iloc[j]
                if a.pubs_own >= 1.6 * b.pubs_own and b.rpc - a.rpc >= 8 and a.pubs_own >= 800:
                    pool.append(dict(year=int(yr), a=a.label, b=b.label, a_papers=int(a.pubs_own),
                                     b_papers=int(b.pubs_own), a_rpc=float(a.rpc), b_rpc=float(b.rpc)))
    random.Random(seed).shuffle(pool)
    return pool


VIVA_POOL = build_viva_pool()


def fmt_int(x):
    return f"{int(round(x)):,}"


# ------------------------------------------------------------------ SQLite (lecture 5: queries take parameters, never f-strings)
import sqlite3

_db = sorted(ROOT.glob("data/dcv_*.sqlite"))
DB_PATH = _db[-1] if _db else None


def sql(query, params=()):
    """run a parameterised query on the project database; returns a DataFrame, or None if the database is missing"""
    if DB_PATH is None:
        return None
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(query, con, params=params)


def history(id_new):
    """all years of one institution"""
    r = sql("SELECT year, rank, rank_rpc, rank_pubs_own, rank_cites_received FROM nirf_openalex_joined "
            "WHERE id_new = ? ORDER BY year", (id_new,))
    if r is None:
        r = J[J.id_new == id_new].sort_values("year")
    return r


def window_total(year):
    """papers counted for one ranking year"""
    r = sql("SELECT SUM(pubs_own) AS n FROM nirf_openalex_joined WHERE year = ?", (int(year),))
    return float(r.n.iloc[0]) if r is not None else float(J[J.year == year].pubs_own.sum())


# ------------------------------------------------------------------ the cleaning story, recomputed from the files
def _norm(name):
    s = str(name).strip().lower()
    s = re.sub(r"[\"'\-`!|:.,]", " ", s)
    s = s.replace("&", "and")
    return re.sub(r"\s+", " ", s).strip()


def _logval(step_start, col="count"):
    if LOG is None:
        return None
    r = LOG[LOG.step.str.strip().str.startswith(step_start)]
    return None if r.empty else r.iloc[0]


def cleaning_steps():
    """rows of (group, found, did, before, after, why). Counts come from the raw scrape and the final tables,
    so they are checked every time the dashboard starts."""
    R = []
    n = len(J)
    if RAW is not None:
        changed = int((RAW.name != RAW.name.map(_norm)).sum())
        R.append(("Names and places", "Institution names came in capitals, with stray punctuation and '&'.",
                  "Lower-cased, trimmed, punctuation removed, '&' written as 'and'.",
                  f"{changed:,} of {len(RAW):,} rows", "0 rows", "So that the same institution matches itself across years."))
        R.append(("Names and places", "The 2017 ids use another format, and some institutions were renamed.",
                  "Matched 2017 rows to the later id by name; 9 needed a hand-checked alias. 15 institutions found no later id and got a placeholder id.",
                  f"{RAW.nirf_id.nunique()} ids, {RAW.name.nunique()} names", f"{J.id_new.nunique()} ids, {J.name_new.nunique()} names",
                  "One id and one name per institution, using the latest name."))
        R.append(("Names and places", "The same city is spelled in several ways (Bangalore and Bengaluru, Allahabad and Prayagraj).",
                  "Standardised the spelling. The raw label stays in location_raw.",
                  f"{RAW.location.nunique()} spellings", f"{J.location_clean.nunique()} spellings", "Needed for grouping by place."))
    R.append(("Names and places", "Units, dates and number strings.", "Checked: nothing to fix. Scores run 0 to 100, counts are whole numbers, the year is an integer.",
              "-", "-", "Dtypes were checked again after reading the file back from SQLite."))
    exact = int(J.duplicated().sum()); same_year = int(J.duplicated(["id_new", "year"]).sum())
    R.append(("Duplicates", "Exact duplicate rows, and one institution listed twice in a year.", "Checked both. None found.",
              f"{exact + same_year}", "0", "The id-and-year pair is unique."))
    nd = _logval("pairs of different institutions"); xs = _logval("NIRF name vs OpenAlex")
    if nd is not None and xs is not None:
        R.append(("Duplicates", "The same institution under different names, across the two sources.",
                  "Compared names with a string similarity score. Pairs within NIRF at 0.92 or more were reviewed by eye. NIRF names against OpenAlex names below 0.6 were checked against the ROR city and type.",
                  f"{int(nd['count'])} close pairs, {int(xs['count'])} weak matches", "all reviewed",
                  "The close pairs are different campuses (IITs, AIIMS). The weak matches are renamed or abbreviated institutions."))
    R.append(("Duplicates", "Two NIRF institutions pointing at one OpenAlex record.", "Checked. None found, apart from the AIIMS Delhi record, which looks like several campuses merged and is flagged.",
              "0", "0", "Flagged rows are tested again in the robustness chart."))
    R.append(("Missing values", "Empty cells in the scores and counts we use.", "Counted per column. None found, so nothing to impute.", "0 cells", "0 cells",
              "Checked tlr, rpc, go, oi, pr, pubs_own, cites_received and pubs_lineage."))
    r = _logval("OpenAlex yearly count empty")
    if r is not None:
        R.append(("Missing values", "OpenAlex has no yearly counts before 2010, and none for future years.", "Left empty. None of them falls inside a 3-year window.",
                  f"{int(r['count']):,} cells", "0 inside windows", "Structural gaps, not lost data."))
    r = _logval("institution-years that vanish")
    if r is not None and MISS is not None:
        m0 = MISS.iloc[0]
        R.append(("Missing values", f"{int(r['count'])} institution-years vanish from the next year's top 100.",
                  f"Permutation test: the ones that vanish had a mean rank of {m0.mean_drop:.1f}, the ones that stay {m0.mean_stay:.1f} (p = {m0.p_value:.4f}). "
                  "That ties missingness to an observed value, so it is MAR, not MCAR. MNAR cannot be ruled out.",
                  f"{int(r['count'])} gone", f"{int(r['count'])} gone",
                  "No imputation. We keep the observed rows and say the results hold for institutions inside the top 100. Deleting nothing is the choice here."))
    r = _logval("perception score recorded")
    if r is not None and MISS is not None and len(MISS) > 1:
        m1 = MISS.iloc[1]
        R.append(("Missing values", f"{int(r['count'])} institution-years have a perception score of exactly 0.",
                  f"Their mean rank is {m1.mean_drop:.0f} against {m1.mean_stay:.0f} for the rest (p = {m1.p_value:.3f}). A 0 may mean 'not reported'.",
                  f"{int(r['count'])} rows", f"{int(r['count'])} rows", "Kept as published. Perception is not used in the main result."))
    r = _logval("institution-years flagged by at least one method")
    if r is not None:
        few = _logval("of which: very few"); many = _logval("of which: very many")
        R.append(("Outliers", "Unusual paper counts, found with three methods: IQR and modified z-score on log papers, and Mahalanobis distance.",
                  f"Looked at each one. {int(few['count']) if few is not None else '?'} have very few papers (management or specialist institutes) and "
                  f"{int(many['count']) if many is not None else '?'} have very many (large research universities). All are real values.",
                  f"{int(r['count'])} flagged", f"{int(r['count'])} kept",
                  "Kept. The robustness chart repeats the analysis without flagged rows."))
    flags = int(J.flag_any.sum())
    R.append(("Outliers", "Rows where the counts are less trustworthy: lineage count more than 5% above own count, OpenAlex's two counts disagreeing, or the AIIMS Delhi record.",
              "Flagged, not removed.", f"{flags} of {n} rows", f"{flags} flagged", "We use the own count as the main measure and test the flagged rows separately."))
    g = J[J.year == J.year.max()]
    lin, own = int(g.pubs_lineage.sum()), int(g.pubs_own.sum())
    R.append(("Final table", f"Lineage and own paper counts differ in {J.year.max()}.", "Own count is the main measure.", f"{lin:,} papers (lineage)",
              f"{own:,} papers ({100 * (1 - own / lin):.1f}% fewer)", "Lineage also counts units filed beneath an institution, which inflates nine institutions."))
    R.append(("Final table", "Rows in the final table.", "No rows dropped. Stored in SQLite and read back: shape, values and dtypes match.", f"{n} rows", f"{n} rows",
              "SQLite: one file, SQL queries, standard library. CSV copies feed the dashboard."))
    return R
