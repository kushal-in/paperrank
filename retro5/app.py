"""
Marks & Margins - retro dashboard for "Does the NIRF research score track OpenAlex output?"
Run:  python app.py   then open http://127.0.0.1:8050
"""
import numpy as np
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
import cbcheck

import data as D
import charts as C
import config as cfg

app = Dash(__name__, title="Marks & Margins", suppress_callback_exceptions=True, update_title=None)
server = app.server

TABS = [("home", "Start"), ("track", "Does it track?"), ("flows", "Who moves"), ("inst", "Pick two"),
        ("land", "Big picture"), ("gaps", "Biggest misses"), ("data", "The data"), ("about", "Credits and limits")]
YEARS = D.YEARS
TOP2 = D.J[D.J.year == D.YEARS[-1]].nsmallest(2, "rank").id_new.tolist()
LAST = YEARS[-1]


# ------------------------------------------------------------------ small building blocks
HIDES = {
    "Who was number one": "Only the top 12 are drawn, and only by research score. An institution at rank 13 never shows.",
    "How closely the two lists agree": "One number per year hides how the agreement differs between the top 50 and the bottom 50.",
    "Score rank to": "Bands hide the size of a move: one place across a band edge looks the same as forty.",
    "Research score against": "The log axis squeezes the big producers together, so gaps among them look smaller than they are.",
    "Agreement in": "A single correlation cannot show the few institutions that are far off the trend.",
    "Agreement over the years": "The bands come from resampling the same 100 institutions. They show sampling noise, not errors in OpenAlex.",
    "Does the result change": "All four versions still use OpenAlex, so an error OpenAlex shares across them would not show up.",
    "Rank bands from": "Only five snapshot years are drawn, so an institution that left and came back looks like it never left.",
    "Output by institution": "Box area is hard to compare, and the small boxes cannot all be labelled.",
    "Who is in the top 100": "It shows counts only. Scores and output are not in this chart.",
    "The five NIRF scores": "The axes are on different scales and the shape changes with their order.",
    "over the years": "Ranks exist only inside the top 100, so a missing point means outside the list, not a bad rank.",
    "The 2025 top 12": "Only institutions that made the 2025 top 12 are drawn.",
    "Rank by year": "Colour shades are coarse. The printed rank carries the detail.",
    "Research score by type": "Types with a handful of institutions give lumpy shapes. The dots show how few there are.",
    "All years together": "A 3D view changes with the angle, smoothing blurs small clusters, and all years are pooled.",
    "All the scores and counts": "Only neighbouring axes can be compared, and the axis order was our choice.",
    "Biggest misses": "A rank gap ignores the size of the score difference. In a crowded middle, 30 places can be a tiny score gap.",
    "Who falls out": "It counts who left, not why. An institution may simply have stopped taking part in NIRF.",
    "Rank gaps by type": "Same limit as the chart above: places, not score points.",
    "Before and after": "Distinct counts show how much was merged, not whether every merge was right.",
    "Rows left after": "A step that keeps every row can still be keeping bad rows.",
    "Own count and lineage": "Only the 14 largest differences are drawn.",
    "One panel per type": "Panels with few institutions give shaky correlations, and pooling nine years counts the same institution many times.",
    "How the scores and counts": "The bin width is our choice and changes how smooth the bars look.",
    "Which scores move together": "A correlation shows association only. It cannot say which score drives which.",
    "Types of institution in the top 100": "Counts only. A type can hold its count while its institutions swap places inside the top 100.",
    "Outliers": "A flag means the methods noticed the point, not that the point is wrong.",
}


def hides_for(title):
    for k, v in HIDES.items():
        if title.startswith(k) or (k in ("over the years",) and k in title):
            return v
    return None

def graph(fig, gid=None, **kw):
    h = fig.layout.height or 420
    return dcc.Graph(id=gid, figure=fig, config=dict(displaylogo=False, responsive=True, scrollZoom=False,
                     modeBarButtonsToRemove=["lasso2d", "select2d", "autoScale2d"]),
                     style={"height": f"{h}px"}, **kw) if gid else dcc.Graph(
        figure=fig, config=dict(displaylogo=False, responsive=True, modeBarButtonsToRemove=["lasso2d", "select2d"]),
        style={"height": f"{h}px"})


def card(title, body, take=None, span=6, i=0, tag=None, cls=""):
    kids = [html.H3(title), body]
    if take:
        kids.append(html.P(take, className="take"))
    h = hides_for(title)
    if take and h:
        kids.append(html.P([html.B("What it hides. "), h], className="hides"))
    return dbc.Col(html.Section(kids, className=f"card {cls}"), width=12, lg=span, className="gcol")


def rows(cols):
    """pack columns into dbc rows whose widths add up to 12"""
    out, cur, tot = [], [], 0
    for c in cols:
        w = c.lg
        if tot + w > 12:
            out.append(dbc.Row(cur, className="grow")); cur, tot = [], 0
        cur.append(c); tot += w
    if cur:
        out.append(dbc.Row(cur, className="grow"))
    return html.Div(out, className="grid")


def stat(num, label, note="", decimals=0, i=0):
    return html.Div([html.Span(className="countup", **{"data-to": f"{num}", "data-dec": str(decimals)}),
                     html.Div(label, className="lab"), html.Div(note, className="note") if note else None], className="stat")


def section_title(text, sub=None):
    return html.Div([html.H2(text), html.P(sub) if sub else None], className="sec-title")


def f2(x): return f"{x:.2f}"


def agree(year, col):
    g = D.J[D.J.year == year]
    return D.rho(g, "rpc", col)


def mcol(metric): return D.METRICS[metric]["col"]


# ------------------------------------------------------------------ layout
def dd(id_, options, value, multi=False, label="", w=200, search=False, ph=None):
    return html.Div([html.Label(label), dcc.Dropdown(id=id_, options=options, value=value, multi=multi, clearable=multi,
                                                      searchable=search, placeholder=ph)], className="ctl", style={"minWidth": f"{w}px"})


app.layout = html.Div([
        html.Header([
        html.Div("Marks & Margins", className="brand"),
        dcc.RadioItems(id="tab", options=[{"label": n, "value": k} for k, n in TABS], value="home", className="nav", inline=True),
    ], className="top"),
    html.Div([
        dd("year", [{"label": str(y), "value": y} for y in YEARS], LAST, label="Ranking year", w=130),
        dd("metric", [{"label": "Papers", "value": "papers"}, {"label": "Citations", "value": "citations"}], "papers", label="Compare with", w=150),
        dd("types", [{"label": t, "value": t} for t in D.TYPES], D.TYPES, multi=True, label="Types of institution", w=330),
        dd("hl", [{"label": "Every type in its own colour", "value": "all"}] + [{"label": "Highlight: " + t, "value": t} for t in D.TYPES],
           "IIT", label="Colour", w=260),
        html.Div([dd("inst-a", D.INSTITUTIONS, TOP2[0], label="Institution A", w=250, search=True),
                  dd("inst-b", D.INSTITUTIONS, TOP2[1], label="Institution B", w=250, search=True)],
                 id="inst-ctl", className="inst-ctl"),
    ], className="controls"),
    html.Main(id="page", className="page"),
    html.Footer([html.Span(f"{cfg.COURSE}. Project {cfg.REF}."), html.Span("Sources: NIRF Overall rankings, OpenAlex (CC0), ROR (CC0). OpenAlex counts are a second opinion on output, not the truth.")], className="foot"),
    dcc.Store(id="sel"),
], className="shell")


@app.callback(Output("inst-ctl", "style"), Input("tab", "value"))
def show_inst(tab):
    return {"display": "flex"} if tab == "inst" else {"display": "none"}


@app.callback(Output("tab", "value"), Input("go-track", "n_clicks"), Input("go-flows", "n_clicks"), Input("go-gaps", "n_clicks"),
              prevent_initial_call=True)
def jump(*clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return no_update
    return {"go-track": "track", "go-flows": "flows", "go-gaps": "gaps"}.get(ctx.triggered_id, no_update)


# ------------------------------------------------------------------ pages
def page_home(year, metric, types):
    per, rk, gp, word, axis = C.metric_cols(metric)
    p0, p1 = agree(YEARS[0], "pubs_own"), agree(LAST, "pubs_own")
    c0, c1 = agree(YEARS[0], "cites_received"), agree(LAST, "cites_received")
    leaders = D.J[D.J["rank"] == 1].groupby("year").label.first()
    names = list(dict.fromkeys(leaders))
    fig_s, stay, n = C.sankey_bands(year, types, metric)
    hero = html.Section([
        html.Div([
            html.H1(["Do NIRF's research scores ", html.Mark("match"), " the research?"]),
            html.P(f"NIRF gives every institution in its top 100 a research score. We checked that score against paper and "
                   f"citation counts from OpenAlex, a source NIRF does not use. That is {D.J.id_new.nunique()} institutions, "
                   f"{len(YEARS)} ranking years and {len(D.J)} rows in all."),
            html.Div([html.Button("Does it track?", id="go-track", className="lnk"),
                      html.Button("Who moves", id="go-flows", className="lnk"),
                      html.Button("Biggest misses", id="go-gaps", className="lnk")], className="links"),
        ], className="hero-text"),
        html.Div([html.Div(graph(C.hero3d(year, types), gid="hero3d"), className="hero-graph"),
                  html.P("Each point is an institution in " + str(year) + ". Drag to turn it around.", className="cap")], className="hero-3d"),
    ], className="hero")
    stats = dbc.Row([
        dbc.Col(stat(D.J.id_new.nunique(), "institutions", "seen in the top 100 at least once"), width=6, lg=3),
        dbc.Col(stat(len(D.J), "institution-years", f"{len(YEARS)} ranking years of about 100 rows"), width=6, lg=3),
        dbc.Col(stat(p1, f"correlation with papers, {LAST}", f"it was {p0:.2f} in {YEARS[0]}", decimals=2), width=6, lg=3),
        dbc.Col(stat(D.window_total(LAST), "papers counted", f"{LAST - 3} to {LAST - 1}, for the {LAST} ranking"), width=6, lg=3),
    ], className="stats")
    cards = [
        card("Who was number one, 2017 to 2025", graph(C.race(types, metric)),
             f"Only {len(names)} institutions have held first place: {' and '.join(names)}. Press play to watch the top 12 shuffle.", span=7),
        card("How closely the two lists agree", html.Div([graph(C.gauge(p1, "")), html.Div(f"Papers, {LAST}", className="cap center"),
                                                         graph(C.gauge(c1, "")), html.Div(f"Citations, {LAST}", className="cap center")]),
             f"In {LAST} the correlation is {p1:.2f} with papers and {c1:.2f} with citations. In {YEARS[0]} it was {p0:.2f} and {c0:.2f}. A value of 1 would mean both lists put institutions in the same order.", span=5),
        card(f"From score rank to {word} rank, {year}", graph(fig_s),
             f"{stay} of {n} institutions land in the same band on both lists. The other {n - stay} move up or down at least one band.", span=12),
    ]
    return [hero, stats, rows(cards)]


def page_track(year, metric, types):
    per, rk, gp, word, axis = C.metric_cols(metric)
    col = mcol(metric)
    s = D.agreement_by_year(col)
    sp, sc = agree(year, "pubs_own"), agree(year, "cites_received")
    top, bot = D.split_by_half(col)
    r_year = D.robustness_table().loc[year]
    cards = [
        card(f"Research score against {word}, year by year", graph(C.anim_scatter(types, metric)),
             f"The correlation was {s.iloc[0]:.2f} in {YEARS[0]} and {s.iloc[-1]:.2f} in {LAST}. The lowest was {s.min():.2f}, in {s.idxmin()}. Press play to watch the points drift.", span=7),
        card(f"Agreement in {year}", html.Div([graph(C.gauge(sp, "")), html.Div("Papers", className="cap center"), graph(C.gauge(sc, "")), html.Div("Citations", className="cap center")]),
             f"In {year} the correlation is {sp:.2f} with papers and {sc:.2f} with citations. Using {word}, it is {top[year]:.2f} among the top 50 and {bot[year]:.2f} among ranks 51 to 100.", span=5),
        card("Agreement over the years", graph(C.corr_line()),
             f"Papers go from {agree(YEARS[0], 'pubs_own'):.2f} to {agree(LAST, 'pubs_own'):.2f}, citations from {agree(YEARS[0], 'cites_received'):.2f} to {agree(LAST, 'cites_received'):.2f}. Shaded bands are 95% bootstrap intervals. The dotted line compares NIRF's overall rank with papers.", span=6),
        card("Does the result change if we count differently?", graph(C.robust_heat()),
             f"In {year} the four ways of counting give between {r_year.min():.2f} and {r_year.max():.2f}. None of them changes the picture much.", span=6),
    ]
    return [section_title("Does the research score follow output?", "Spearman rank correlation: 1 means both lists order institutions the same way, 0 means no link."),
            rows(cards)]


def page_flows(year, metric, types):
    per, rk, gp, word, axis = C.metric_cols(metric)
    fig_s, stay, n = C.sankey_bands(year, types, metric)
    fig_y, moved, tot = C.sankey_years(types)
    g = D.J[D.J.year == year]
    g = g[g.type.isin(types)] if types else g
    big = g.loc[g[gp].abs().idxmax()] if len(g) else None
    tc = g.type.value_counts()
    fig_t, tt_ = C.type_stack(types)
    delta = (tt_.loc[YEARS[-1]] - tt_.loc[YEARS[0]]) if len(tt_) else None
    if delta is not None and len(delta):
        up, dn = delta.idxmax(), delta.idxmin()
        tstack_txt = (f"{up} went from {int(tt_.loc[YEARS[0], up])} institutions in {YEARS[0]} to {int(tt_.loc[YEARS[-1], up])} in {YEARS[-1]}. "
                      f"{dn} went from {int(tt_.loc[YEARS[0], dn])} to {int(tt_.loc[YEARS[-1], dn])}.")
    else:
        tstack_txt = "No institutions selected."
    cards = [
        card(f"Score rank to {word} rank, {year}", graph(fig_s),
             f"{stay} of {n} institutions stay in the same band on both lists. The ribbons that cross show the disagreements.", span=6),
        card("Rank bands from 2017 to 2025", graph(fig_y),
             f"{moved} of the {tot} institutions seen in 2017 or 2025 sit in a different band by 2025. Some left the top 100 altogether.", span=6),
        card(f"Output by institution, {year}", graph(C.treemap(year, types, metric)),
             (f"Box size is {word} per year and colour is the rank gap. {big['label']} has the largest gap, {big[gp]:+.0f} places." if big is not None else "No institutions selected."), span=7),
        card(f"Who is in the top 100, {year}", graph(C.sunburst(year, types)),
             (f"{tc.index[0]} is the biggest group, with {tc.iloc[0]} of {len(g)} institutions. The outer ring splits each group by rank band." if len(g) else "No institutions selected."), span=5),
        card("Types of institution in the top 100, year by year", graph(fig_t), tstack_txt, span=12),
    ]
    return [section_title("Who moves when we count papers instead?", "Same institutions, ranked two ways: by NIRF's research score and by what OpenAlex counts. Ribbon width is the number of institutions."), rows(cards)]


def page_inst(year, metric, types, ia, ib):
    na = D.J[D.J.id_new == ia].name.iloc[0]; nb = D.J[D.J.id_new == ib].name.iloc[0]
    ra = D.J[(D.J.id_new == ia) & (D.J.year == year)]; rb = D.J[(D.J.id_new == ib) & (D.J.year == year)]
    if len(ra) and len(rb):
        ra, rb = ra.iloc[0], rb.iloc[0]
        rad = (f"In {year}, {ra['label']} scored {ra.rpc:.1f} on research and {rb['label']} scored {rb.rpc:.1f}. "
               f"They published about {D.fmt_int(ra.pubs_own / 3)} and {D.fmt_int(rb.pubs_own / 3)} papers a year.")
    else:
        rad = f"One of the two is not in the top 100 in {year}. Try another year."
    ga = D.J[D.J.id_new == ia].sort_values("year")
    spread = (ga["rank"] - ga.rank_pubs_own).abs().max()
    j = D.J[D.J.type.isin(types)] if types else D.J
    t17 = set(j[j.year == YEARS[0]].nsmallest(12, "rank").id_new); t25 = set(j[j.year == LAST].nsmallest(12, "rank").id_new)
    jj = D.J[D.J.type.isin(types)] if types else D.J
    top30 = jj.pivot_table(index="label", columns="year", values="rank")
    top30 = top30.loc[top30.mean(axis=1).sort_values().index[:30]]
    n_all = int(top30.notna().all(axis=1).sum())
    cards = [
        card("The five NIRF scores, side by side", graph(C.radar(ia, ib, year)), rad, span=5),
        card(f"{na} over the years", graph(C.trajectory(ia)),
             f"Its NIRF rank and its rank by papers differ by up to {spread:.0f} places in a single year. The solid line is NIRF's rank; the others come from our counts.", span=7),
        card(f"{nb} over the years", graph(C.trajectory(ib)), f"The same four ranks for institution B. Its rank by papers and its NIRF rank differ by up to {(D.J[D.J.id_new == ib].eval('rank - rank_pubs_own').abs().max()):.0f} places in one year.", span=6),
        card("The 2025 top 12, looking back", graph(C.bump(types)),
             f"{len(t17 & t25)} of the 2025 top 12 were also in the 2017 top 12. Line colour and marker shape show the type of institution.", span=6),
        card("Rank by year for the 30 best-ranked institutions", graph(C.rank_heat(types)),
             f"{n_all} of these 30 institutions were in the top 100 in all nine years. Darker is better, and blank cells are years outside the list.", span=12),
    ]
    return [section_title("Pick two institutions", "Change A and B in the bar above."), rows(cards)]


def page_land(year, metric, types):
    per, rk, gp, word, axis = C.metric_cols(metric)
    g = D.J[D.J.year == year]
    g = g[g.type.isin(types)] if types else g
    med = g.groupby("type").rpc.median().sort_values()
    peak = np.median(D.J.papers_per_year)
    comp = {n: D.rho(g, c, "pubs_own") for n, c in [("Teaching", "tlr"), ("Research", "rpc"), ("Graduation", "go"), ("Outreach", "oi"), ("Perception", "pr")]}
    best = max(comp, key=lambda k: comp[k] if pd.notna(comp[k]) else -9)
    fig_sm, rho_t, n_t = C.small_multiples(metric, types)
    ok = {t: v for t, v in rho_t.items() if pd.notna(v) and n_t[t] >= 20}
    if ok:
        hi_t, lo_t = max(ok, key=ok.get), min(ok, key=ok.get)
        sm_txt = (f"Agreement is highest for {hi_t} (rho {ok[hi_t]:.2f}, {n_t[hi_t]} institution-years) and lowest for {lo_t} (rho {ok[lo_t]:.2f}, {n_t[lo_t]}). "
                  f"All panels share the same axes, so the slopes can be compared directly.")
    else:
        sm_txt = "Too few institutions selected to compare panels."
    fig_ch, rmat = C.corr_heat(year, types)
    if len(g) > 5:
        others = rmat.loc[["Teaching", "Graduation", "Outreach", "Perception"], "Papers"]
        ch_txt = (f"Research score has a rank correlation of {rmat.loc['Research', 'Papers']:.2f} with papers in {year}. "
                  f"Of the other NIRF scores, {others.idxmax()} comes closest at {others.max():.2f}, and {others.idxmin()} is the furthest at {others.min():.2f}.")
    else:
        ch_txt = "Too few institutions selected."
    sc, pp = g.rpc, g.papers_per_year
    hist_txt = (f"In {year} the median research score is {sc.median():.1f}, and {int((sc < 30).sum())} of {len(g)} institutions score below 30 while {int((sc > 60).sum())} score above 60. "
                f"The median institution publishes about {D.fmt_int(pp.median())} papers a year, but the biggest publishes {D.fmt_int(pp.max())}.") if len(g) else "No institutions selected."
    cards = [
        card(f"Research score by type of institution, {year}", graph(C.violin_type(year, types)),
             (f"{med.index[-1]} has the highest median research score ({med.iloc[-1]:.1f}) and {med.index[0]} the lowest ({med.iloc[0]:.1f}). "
              f"Inside {med.index[-1]} the scores run from {g[g.type == med.index[-1]].rpc.min():.1f} to {g[g.type == med.index[-1]].rpc.max():.1f}, so the type alone does not settle the score." if len(med) else "No institutions selected."), span=6),
        card("All years together, in 3D", graph(C.surface3d()),
             f"The typical institution publishes about {D.fmt_int(peak)} papers a year. The ridge climbs to the right: more papers usually goes with a higher score. Drag to turn it.", span=6),
        card("One panel per type of institution, all years", graph(fig_sm), sm_txt, span=12),
        card(f"How the scores and counts are spread, {year}", graph(C.histograms(year, types)), hist_txt, span=7),
        card(f"Which scores move together, {year}", graph(fig_ch), ch_txt, span=5),
        card(f"All the scores and counts at once, {year}", graph(C.parcoords(year, types)),
             f"Of the five NIRF scores, {best} follows papers most closely in {year} (correlation {comp[best]:.2f}). Drag along any axis to pick a range.", span=12),
    ]
    return [section_title("The big picture"), rows(cards)]


def page_gaps(year, metric, types):
    per, rk, gp, word, axis = C.metric_cols(metric)
    g = D.J[D.J.year == year]
    g = g[g.type.isin(types)] if types else g
    fig_d, nleave, nleave_low = C.dropouts()
    if len(g):
        up, dn = g.loc[g[gp].idxmax()], g.loc[g[gp].idxmin()]
        txt = f"{up['label']} ranks {up[gp]:.0f} places lower on {word} than on research score. {dn['label']} ranks {abs(dn[gp]):.0f} places higher."
    else:
        txt = "No institutions selected."
    if len(g):
        mg = g.groupby("type")[gp].median().sort_values()
        gv_txt = (f"Median gap is {mg.iloc[-1]:+.0f} places for {mg.index[-1]} and {mg.iloc[0]:+.0f} for {mg.index[0]}. "
                  "A gap above zero means the research score ranks an institution higher than its output does.")
    else:
        gv_txt = "No institutions selected."
    cards = [
        card(f"Biggest misses, {year}", graph(C.lollipop(year, types, metric)), txt, span=7),
        card("Who falls out of the top 100", graph(fig_d),
             f"{nleave} institution-years disappear from the next year's list, and {nleave_low} of them were ranked 51 or lower. Most of the churn is near the bottom.", span=5),
        card("Rank gaps by type of institution", graph(C.violin_type(year, types, gp, f"Rank gap on {word} (places)")),
             gv_txt, span=12),
    ]
    return [section_title("Where the two lists disagree most"), rows(cards)]


def page_data(year, metric, types):
    fig_b, (bf, af) = C.before_after()
    fig_l, nl = C.lineage_dumbbell()
    n_out = len(D.OUT) if D.OUT is not None else 0
    log_rows, last = [], None
    for grp, found, did, before, after, why in D.cleaning_steps():
        if grp != last:
            log_rows.append(html.Tr(html.Td(grp, colSpan=5, className="grp")))
            last = grp
        log_rows.append(html.Tr([html.Td(found), html.Td(did), html.Td(before, className="num"), html.Td(after, className="num"), html.Td(why)]))
    cards = [
        card("Before and after cleaning", graph(fig_b),
             (f"The raw scrape had {bf[0]} NIRF ids for {af[0]} real institutions, and {bf[1]} spellings of {af[1]} names. Cleaning merged them." if bf else "Raw file not found."), span=6),
        card("Rows left after each step", graph(C.missing_funnel()),
             f"All {len(D.J)} institution-years match OpenAlex with a full 3-year window. {int((~D.J.flag_any).sum())} pass every quality flag.", span=6),
        card("Own count and lineage count, 2025", graph(fig_l),
             f"{nl} institutions have a lineage count more than 5% above their own count, so we use the own count. "
             f"The largest difference is {D.J[D.J.year == 2025].nlargest(1, 'lineage_ratio').label.iloc[0]}, where the lineage count is {D.J[D.J.year == 2025].lineage_ratio.max():.2f} times its own.", span=6),
        card("Outliers", graph(C.outliers_plot()),
             f"Three methods flagged {n_out} institution-years. All look genuine (very large or very small institutions), so we kept them.", span=6),
        card("Cleaning log", html.Div(html.Table([html.Thead(html.Tr([html.Th("What we found"), html.Th("What we did"), html.Th("Before"), html.Th("After"), html.Th("Why")])), html.Tbody(log_rows)], className="tbl"), className="tbl-wrap"),
             "One line per cleaning step with the rows it touched. Every count here is recomputed from the raw and final files when the dashboard starts, so it matches the data.", span=12),
    ]
    return [section_title("How the data was collected and cleaned", "NIRF pages and the OpenAlex API, cleaned in Python and stored in SQLite."), rows(cards)]


LIMITS = [
    "Sankey, radar, gauge, 3D surface and bootstrap intervals go beyond what the lectures cover. We added them to show the data from more angles.",
    "NIRF documents a 3-year publication window for universities and colleges. We found nothing for the Overall category and assumed the same.",
    "OpenAlex coverage and affiliations are imperfect, especially for institutions with several campuses. Its counts are a second opinion.",
    "NIRF scores are adjusted for faculty strength. Our counts are not, so large institutions may look better on raw output.",
    "The AIIMS Delhi record in OpenAlex seems to merge several AIIMS campuses, so it is flagged.",
    "Institution types come from keyword rules on the name, not from an official list.",
    "The research score also includes patents and funding, which OpenAlex does not measure.",
    "A high correlation does not prove NIRF is right, and a low one does not prove it is wrong. It only says whether two independent views order institutions alike.",
]


def page_about():
    t = lambda head, rows: html.Table([html.Thead(html.Tr([html.Th(h) for h in head])), html.Tbody([html.Tr([html.Td(c) for c in r]) for r in rows])], className="tbl")
    cards = [
        card("Team and contributions", t(["Name", "Roll no.", "Contribution"], cfg.TEAM), None, span=12),
        card("Data sources and licences", t(["Source", "What we took", "Licence or terms", "Retrieved"], cfg.SOURCES), None, span=12),
        card("Libraries and fonts", t(["Tool", "Licence"], cfg.LIBRARIES), None, span=6),
        card("AI tools", t(["Tool", "How it was used"], cfg.AI_TOOLS), None, span=6),
        card("Colour check", html.Table([html.Thead(html.Tr([html.Th("Vision"), html.Th("Closest pair of colours"), html.Th("Distance (CIELAB)")])),
             html.Tbody([html.Tr([html.Td(n), html.Td(f"{p[0]} and {p[1]}"), html.Td(f"{d:.1f}")]) for n, (d, p) in
                         [(n, cbcheck.closest(C.TYPE_COL_ALL, M)) for n, M in [("Normal", None), ("Deuteranopia", cbcheck.M_DEUT), ("Protanopia", cbcheck.M_PROT)]]])], className="tbl"),
             "The eight type colours are the Okabe-Ito palette. Marker shapes carry the type as well, so colour is never the only cue. The default view uses one highlight colour and grey.", span=12),
        card("Limitations", html.Ol([html.Li(x) for x in LIMITS], className="limits"), None, span=12),
    ]
    return [section_title("Credits and limits"), rows(cards)]


@app.callback(Output("sel", "data"), Input("year", "value"), Input("metric", "value"), Input("types", "value"), Input("hl", "value"))
def keep_selection(year, metric, types, hl):
    """the shared selection lives in a Store, so every page reads the same choices"""
    return dict(year=year, metric=metric, types=types or D.TYPES, hl=hl)


@app.callback(Output("page", "children"), Input("tab", "value"), Input("sel", "data"),
              Input("inst-a", "value"), Input("inst-b", "value"))
def render(tab, sel, ia, ib):
    if not sel:
        return no_update
    year, metric, types = sel["year"], sel["metric"], sel["types"]
    C.set_highlight(sel["hl"])
    fn = {"home": page_home, "track": page_track, "flows": page_flows, "land": page_land, "gaps": page_gaps, "data": page_data}
    if tab == "inst":
        body = page_inst(year, metric, types, ia, ib)
    elif tab == "about":
        body = page_about()
    else:
        body = fn[tab](year, metric, types)
    return html.Div(body, id=f"pg-{tab}", className="pg")


# the home-page buttons must exist for the jump callback; keep hidden stubs so it is always valid
if __name__ == "__main__":
    try:
        app.run(debug=False, port=8050)
    except AttributeError:
        app.run_server(debug=False, port=8050)
