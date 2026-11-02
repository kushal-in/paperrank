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
