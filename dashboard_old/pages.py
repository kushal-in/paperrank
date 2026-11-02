"""
pages.py - the content of each tab. Each function returns Dash components.
The red-margin remarks are written as sentences with numbers filled in from the data,
so they change when you change the year or the measure.
"""
import numpy as np
import pandas as pd
from dash import html, dcc
import data as D
import charts as C
import config as K

GCFG = {"displayModeBar": False, "responsive": True}


def graph(fig):
    return dcc.Graph(figure=fig, config=GCFG, className="graph", style={"height": f"{fig.layout.height or 420}px"})


def sheet(margin, canvas, cls=""):
    return html.Div(className=f"sheet {cls}".strip(), children=[
        html.Div(className="margin", children=margin),
        html.Div(className="canvas", children=canvas)])


def rem(text):
    return html.P(text, className="remark")


def note(text):
    return html.P(text, className="note")


def table(header, rows, cls="tbl", highlight=None):
    head = html.Thead(html.Tr([html.Th(h) for h in header]))
    body = html.Tbody([html.Tr([html.Td(c) for c in r], className=("hl" if highlight is not None and i == highlight else ""))
                       for i, r in enumerate(rows)])
    return html.Table([head, body], className=cls)


def sign_words(gap):
    return "output ranks higher" if gap < 0 else "score ranks higher"


# ------------------------------------------------------------------ home
def home():
    pap, cit = D.agreement_by_year("pubs_own"), D.agreement_by_year("cites_received")
    y0, y1 = int(pap.index.min()), int(pap.index.max())
    top, bot = D.split_by_half("pubs_own")
    n_inst = D.J.id_new.nunique()
    slip = html.Div(className="slip", children=[
        html.Div(f"Application for revaluation, ref. {K.REF}", className="slip-ref"),
        html.H2("Is the NIRF research mark right?", className="slip-title"),
        table(["", ""], [
            ["Script", "NIRF Overall research score (RPC), top 100"],
            ["Years", f"{y0} to {y1}, {n_inst} institutions"],
            ["Re-checked against", "OpenAlex papers and citations, 3 years before each ranking"],
            [f"Agreement, {y0}", html.B(f"{pap[y0]:.2f}")],
            [f"Agreement, {y1}", html.B(f"{pap[y1]:.2f}")],
        ], cls="tbl slip-tbl"),
        html.Div("Result", className="slip-label"),
        html.Div("Marks upheld, with remarks", className="slip-result"),
        html.P(f"The research score still tracks real output (rank correlation {pap[y1]:.2f} with papers and {cit[y1]:.2f} "
               f"with citations in {y1}), but the match is looser among institutions ranked 51 to 100 "
               f"({bot[y1]:.2f}) than in the top 50 ({top[y1]:.2f}).", className="slip-text"),
        html.Div(className="slip-links", children=[
            html.Button("See Q1: Does it track?", id="go-q1", n_clicks=0),
            html.Button("See Q2: Who was re-marked?", id="go-q2", n_clicks=0),
            html.Button("Try the viva", id="go-viva", n_clicks=0)]),
    ])
    side = html.Div(className="slip-side", children=[
        html.Div("RE-CHECKED", className="stamp"),
        html.Div(["Top 50: solid.", html.Br(), "Bottom 50: ask again."], className="hand slip-hand"),
    ])
    return html.Div(className="home", children=[slip, side])


# ------------------------------------------------------------------ Q1
def q1(sub, year, metric, theme):
    m = D.METRICS[metric]
    if sub == "years":
        pap, cit = D.agreement_by_year("pubs_own"), D.agreement_by_year("cites_received")
        margin = [
            rem(f"In {year}, the research score and paper counts agreed at {pap[year]:.2f}. With citations, {cit[year]:.2f}."),
            rem(f"Across the years, agreement with papers ran from {pap.min():.2f} in {int(pap.idxmin())} to "
                f"{pap.max():.2f} in {int(pap.idxmax())}. Zero would mean no link at all."),
            note("Agreement is Spearman rank correlation, about 100 institutions per year. "
                 "The shaded band is a 95% bootstrap interval for papers."),
        ]
        return sheet(margin, graph(C.agreement(theme, year)))
    if sub == "year":
        g = D.J[D.J.year == year]
        r = D.rho(g, "rpc", m["col"])
        big = g.loc[g[m["gap"]].abs().idxmax()]
        word = "higher on output than its score suggests" if big[m["gap"]] < 0 else "higher on score than its output suggests"
        margin = [
            rem(f"In {year}, {len(g)} institutions are ranked. Rank correlation between research score and {m['word']}: {r:.2f}."),
            rem(f"The widest gap is {big.label}: NIRF rank {int(big['rank'])}, but {int(big[m['rank']])} by {m['word']}. "
                f"That is {abs(int(big[m['gap']]))} places {word}."),
            note("Square outlines: NIRF ranks 1 to 50. Filled dots: ranks 51 to 100. The horizontal axis is on a log scale."),
        ]
        return sheet(margin, graph(C.scatter_year(theme, year, metric)))
    # split
    top, bot = D.split_by_half(m["col"])
    margin = [
        rem(f"In {year}, institutions ranked 1 to 50 agree with {m['word']} at {top[year]:.2f}; those ranked 51 to 100 at {bot[year]:.2f}."),
        rem(f"The lower half's agreement has ranged from {bot.min():.2f} ({int(bot.idxmin())}) to {bot.max():.2f} ({int(bot.idxmax())}); "
            f"the top half's from {top.min():.2f} to {top.max():.2f}."),
        note("Part of the drop may be that scores in the lower half sit closer together. We have not tested that."),
    ]
    return sheet(margin, graph(C.split_halves(theme, metric, year)))


# ------------------------------------------------------------------ Q2
def q2(sub, year, metric, theme):
    m = D.METRICS[metric]
    g = D.J[D.J.year == year]
    gap = m["gap"]
    if sub == "gaps":
        a, b = g.loc[g[gap].idxmin()], g.loc[g[gap].idxmax()]
        margin = [
            rem(f"In {year}, {a.label} ranks {int(a.rank_rpc)} on research score but {int(a[m['rank']])} by {m['word']}: "
                f"{abs(int(a[gap]))} places better on output."),
            rem(f"{b.label} is the reverse: {int(b.rank_rpc)} on score, {int(b[m['rank']])} by {m['word']}, "
                f"{abs(int(b[gap]))} places lower on output."),
            note("The score also rewards things papers do not count, and may adjust for faculty size. "
                 "OpenAlex counts are a second opinion, not a verdict."),
        ]
        return sheet(margin, graph(C.gaps(theme, year, metric)))
    if sub == "slope":
        med, mx = g[gap].abs().median(), g[gap].abs().max()
        margin = [
            rem(f"Each line joins one institution's research-score rank (left) to its rank by {m['word']} (right). "
                "Flat lines mean the two agree."),
            rem(f"In {year}, the typical institution sits {med:.0f} places apart on the two rankings; the widest gap is {int(mx)}."),
            note("Highlighted: the eight widest gaps. Solid blue: output ranks higher. Dashed violet: score ranks higher."),
        ]
        return sheet(margin, graph(C.slope(theme, year, metric)))
    med = g.groupby("type")[gap].agg(["median", "size"]).sort_values("median")
    lo, hi = med.iloc[0], med.iloc[-1]
    margin = [
        rem(f"In {year}, {med.index[-1]} have the largest median gap ({hi['median']:+.0f} places, n={int(hi['size'])}): "
            "their score ranks higher than their output."),
        rem(f"{med.index[0]} sit at the other end ({lo['median']:+.0f} places, n={int(lo['size'])}): output ranks higher than the score."),
        note("Types were assigned by a keyword rule. Edit institution_types.csv to correct any label."),
    ]
    return sheet(margin, graph(C.by_type(theme, year, metric)))


# ------------------------------------------------------------------ marksheet
def marksheet(year, metric, theme, ids):
    m = D.METRICS[metric]
    ids = [i for i in ids if i]
    if not ids:
        return sheet([rem("Choose an institution above to see its record.")], html.Div())
    a = D.J[D.J.id_new == ids[0]].sort_values("year")
    nm = a.name.iloc[0]
    row = a[a.year == year]
    margin = []
    if len(row):
        r = row.iloc[0]
        margin.append(rem(f"In {year}, {nm} ranked {int(r['rank'])} on NIRF and {int(r[m['rank']])} by {m['word']} "
                          f"among that year's top 100."))
    else:
        margin.append(rem(f"{nm} was not in the top 100 in {year}."))
    margin.append(rem(f"It appears in {len(a)} of {len(D.YEARS)} years, {int(a.year.min())} to {int(a.year.max())}."))
    if len(ids) > 1:
        b = D.J[D.J.id_new == ids[1]]
        if len(b):
            margin.append(rem(f"For comparison, {b.name.iloc[0]} appears in {len(b)} years."))
    margin.append(note("Lower rank numbers are better. Solid line: research-score rank. Dashed line: rank by "
                       f"{m['word']}."))
    rows = [[int(r.year), int(r["rank"]), f"{r.rpc:.1f}", D.fmt_int(r.pubs_own), int(r.rank_pubs_own),
             D.fmt_int(r.cites_received), f"{int(r[m['gap']]):+d}"] for _, r in a.iterrows()]
    hl = next((i for i, (_, r) in enumerate(a.iterrows()) if int(r.year) == year), None)
    tbl = table(["Year", "NIRF rank", "Research score", "Papers (3 yrs)", "Rank by papers", "Citations (3 yrs)",
                 f"Gap ({m['word']})"], rows, cls="tbl marks", highlight=hl)
    return sheet(margin, [graph(C.marksheet(theme, ids, metric)), html.Div(tbl, className="tbl-wrap")])


# ------------------------------------------------------------------ viva
def viva():
    margin = [
        rem("Viva: the examiner asks, you answer. Two institutions, same year. One has far more papers."),
        rem("Which one got the higher NIRF research score?"),
        html.P(id="viva-score", className="remark"),
        note("Questions are drawn from real pairs where the institution with many more papers scored lower."),
    ]
    canvas = [html.Div(id="viva-question", className="viva-q"),
              html.Div(className="viva-buttons", children=[
                  html.Button(id="viva-a", n_clicks=0, className="viva-btn"),
                  html.Button(id="viva-b", n_clicks=0, className="viva-btn")]),
              html.Div(id="viva-result", className="viva-r"),
              html.Button("Next question", id="viva-next", n_clicks=0, className="viva-next")]
    return sheet(margin, canvas)


# ------------------------------------------------------------------ Q3
def q3(sub, theme):
    if sub == "robust":
        tab = D.robustness_table()
        spread = (tab.max(axis=1) - tab.min(axis=1))
        margin = [
            rem(f"Four ways of counting give almost the same story. In any single year they differ by at most {spread.max():.2f}."),
            rem(f"The low point (2023) shows up in all four, between {tab.loc[2023].min():.2f} and {tab.loc[2023].max():.2f}."),
            note("Lineage count adds units filed beneath an institution. Flagged institutions are those with inflated "
                 "or inconsistent OpenAlex counts."),
        ]
        return sheet(margin, graph(C.robustness(theme)))
    drop, stay = D.dropout_stats()
    items = [
        ("Only the top 100 are ranked.", f"Institutions that vanish the next year had an average rank of {drop.mean():.0f}, "
                                          f"against {stay.mean():.0f} for those that stay. Results describe institutions inside the top 100 only."),
        ("The score is not just papers.", "NIRF's research score also includes citations quality, patents and footprint, and may be "
                                          "scaled by faculty size. We have no faculty numbers, so a gap is not an error."),
        ("The window for Overall is an assumption.", "NIRF states 3 years for universities and colleges. We assumed the same for Overall "
                                                     "and tested a one-year shift."),
        ("OpenAlex is itself imperfect.", "Affiliations are matched by software. Calicut, JNU (2020) and a few others show "
                                          "inconsistent counts and are flagged."),
        ("Boundaries differ.", "Where OpenAlex files units beneath an institution (KLE, Kashmir, Amity, BHU, Delhi), the lineage "
                               "count runs 25 to 40% higher. We use the own count."),
        ("Matching used judgement.", "164 institutions were matched by name, city and ROR. Seven needed a manual choice."),
        ("The two sources share ancestry.", "NIRF's score is built from publication data, so some agreement is expected."),
    ]
    margin = [rem("Seven things to keep in mind before trusting any number here."),
              note("None of these changes the headline, but each limits how far it can be pushed.")]
    return sheet(margin, html.Ol([html.Li([html.B(a + " "), b]) for a, b in items], className="limits"))


# ------------------------------------------------------------------ method
def method(sub, theme):
    if sub == "collect":
        n_rows = len(D.J)
        flow = html.Div(className="flow", children=[
            html.Div([html.B("1 Scrape"), html.Span(f"{n_rows} NIRF rows, 9 years")]),
            html.Div([html.B("2 Clean"), html.Span("342 ids to 164 institutions")]),
            html.Div([html.B("3 Match"), html.Span("164 ROR ids, 7 manual")]),
            html.Div([html.B("4 Collect"), html.Span("OpenAlex, 164 institutions")]),
            html.Div([html.B("5 Join"), html.Span("3-year windows")]),
            html.Div([html.B("6 Store"), html.Span("SQLite and CSV")]),
        ])
        src = table(["Source", "What we took", "Licence or terms", "Retrieved"], [list(s) for s in K.SOURCES], cls="tbl wide")
        margin = [rem("Three sources: NIRF for the marks, ROR to match names to records, OpenAlex for the evidence."),
                  rem(f"Each raw file is kept as downloaded, with its date in the file name, and every row of the final table traces back to one."),
                  note("Raw JSON and HTML are kept in raw/, working files in interim/, final tables in clean/.")]
        return sheet(margin, [flow, src])
    if sub == "clean":
        return clean(theme)
    if sub == "store":
        dd = D.DD
        rows = [] if dd is None else [[r.column, r.meaning, r.unit, r.source] for _, r in dd.iterrows()]
        tree = html.Pre("project/\n  raw/        pages and API responses, as downloaded\n  interim/    scraped, matched and tested tables, logs\n"
                        "  clean/      final tables and the data dictionary\n  data/       dcv_<date>.sqlite (five tables)\n  dashboard/  this app",
                        className="tree")
        margin = [rem("Raw, interim and clean files sit in separate folders. File names carry the source and the date."),
                  rem("SQLite holds the joined table, the OpenAlex tables, the raw scrape and the cleaning log. Reloading the joined table gives identical values, missing cells and types."),
                  note("The data dictionary below lists every column of the joined table.")]
        return sheet(margin, [tree, html.Div(table(["Column", "Meaning", "Unit", "Source"], rows, cls="tbl wide small"), className="tbl-wrap tall")])
    # credits
    margin = [rem("Who did what, and what we used."),
              note("Data are credited with their licences; code libraries with theirs; AI tools as the course asks.")]
    return sheet(margin, [
        html.H3("Contributions"), table(["Member", "Roll no.", "Contribution"], [list(t) for t in K.TEAM], cls="tbl wide"),
        html.H3("Data sources"), table(["Source", "Used for", "Licence or terms", "Retrieved"], [list(s) for s in K.SOURCES], cls="tbl wide"),
        html.H3("Libraries and fonts"), table(["Name", "Licence"], [list(s) for s in K.LIBRARIES], cls="tbl wide"),
        html.H3("AI tools"), table(["Tool", "How it was used"], [list(s) for s in K.AI_TOOLS], cls="tbl wide"),
    ])


def clean(theme):
    ba_fig, (before, after) = C.before_after_counts(theme)
    drop, stay = D.dropout_stats()
    miss_p = None
    if D.MISS is not None and len(D.MISS):
        miss_p = D.MISS.p_value.iloc[0]
    out_n = 0 if D.OUT is None else len(D.OUT)
    n_dup = 0 if D.NEARDUP is None else len(D.NEARDUP)
    n_x = 0 if D.XSRC is None else len(D.XSRC)
    pz = int((D.J.pr == 0).sum())
    sections = [
        sheet([rem(f"Labels. The raw scrape had {before[0]} ids, {before[1]} name spellings and {before[2]} location spellings. "
                   f"After cleaning there are {after[0]} institutions and {after[2]} locations."),
               rem("Papers. Using the own count instead of the lineage count removed the double counting of units filed beneath an institution (for example IIT BHU inside BHU)."),
               note("Cleaning log entries and counts are in the table at the bottom.")],
              [graph(ba_fig), graph(C.lineage_vs_own(theme))]),
        sheet([rem(f"Missing. There are no empty scores. The real gap is institutions leaving the top 100: those that vanish the next year averaged rank {drop.mean():.0f}, "
                   f"against {stay.mean():.0f} for those that stay" + (f" (permutation test p = {miss_p:.4f})." if miss_p is not None else ".")),
               rem(f"So the missingness depends on the rank itself. We keep the observed rows and impute nothing. {pz} perception scores of exactly 0 are kept as published."),
               note("Decision: no imputation, because filling in a rank-100 dropout would invent data the ranking never published.")],
              graph(C.dropout_plot(theme))),
        sheet([rem(f"Outliers. Three tests (IQR, modified z, Mahalanobis) flagged {out_n} institution-years: IIMs and other small institutes with very few papers, plus IISc in 2017."),
               rem("Each is a real institution. None was removed; a run without the flagged rows gives nearly the same result (see Q3)."),
               note("Flagged points are circled in red. Hover for the tests that flagged them.")],
              graph(C.outliers_plot(theme))),
        sheet([rem(f"Duplicates. No institution appears twice in a year, and no two institutions share an OpenAlex record."),
               rem(f"{n_dup} pairs of different institutions have near-identical names (the IIT, IISER and AIIMS campuses) and were kept apart. "
                   f"{n_x} institutions are named differently in NIRF and OpenAlex (for example UPES and the University of Petroleum and Energy Studies); each was checked by city and type."),
               note("Cross-source check: name similarity between NIRF and OpenAlex below 0.6 was reviewed by hand.")],
              html.Div(table(["NIRF name", "OpenAlex name", "Similarity"],
                             [] if D.XSRC is None else [[r.name_new, r.display_name, f"{r.sim:.2f}"] for _, r in D.XSRC.iterrows()],
                             cls="tbl wide small"), className="tbl-wrap tall")),
    ]
    log_tbl = []
    if D.LOG is not None:
        log_tbl = [html.H3("Cleaning log"), html.Div(table(["Area", "Step", "Count", "Detail"],
                   [[r.area, r.step, r["count"], ("" if str(r.detail) == "nan" else str(r.detail)[:140])] for _, r in D.LOG.iterrows()], cls="tbl wide small"),
                   className="tbl-wrap tall")]
    return html.Div(sections + [html.Div(log_tbl, className="logwrap")])
