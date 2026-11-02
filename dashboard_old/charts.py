"""
charts.py - every figure in the dashboard.

Every function takes a theme dict from THEMES, so the same chart is drawn in the
"revaluation" look or the "sarkari" look. The data and the encodings are identical in both;
only colours and fonts change. Hollow squares / filled circles / dash styles carry the meaning,
so the charts still read in greyscale.
"""
import numpy as np
import plotly.graph_objects as go
import data as D

THEMES = {
    "revaluation": dict(
        paper="#F6F8F5", grid="#DCE6F2", rule="#B9CBE3", ink="#23262B", muted="#4a5160",
        a="#3E6FD8",        # OpenAlex, papers
        a2="#1F3F86",       # OpenAlex, citations (darker, dashed)
        b="#4B2E83",        # NIRF
        red="#C62828", soft="#B7C0CC",
        font="Anek Latin, Arial, sans-serif", hand="Kalam, 'Comic Sans MS', cursive", hand_size=16,
    ),
    "sarkari": dict(
        paper="#FFFFFF", grid="#D9D9D9", rule="#888888", ink="#000000", muted="#444444",
        a="#0B3D91", a2="#E07B00", b="#6A1B9A", red="#B00020", soft="#BBBBBB",
        font="Arial, Helvetica, sans-serif", hand="'Times New Roman', serif", hand_size=14,
    ),
}


def T(theme):
    return THEMES.get(theme, THEMES["revaluation"])


def base(theme, title, xtitle=None, ytitle=None, height=420, legend=True):
    t = T(theme)
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, x=0.0, xanchor="left", y=0.975, yanchor="top", font=dict(size=15, color=t["ink"], family=t["font"])),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=t["font"], color=t["ink"], size=12),
        margin=dict(l=62, r=18, t=(92 if legend else 62), b=54), height=height,
        xaxis=dict(title=xtitle, gridcolor=t["grid"], linecolor=t["rule"], zeroline=False, ticks="outside",
                   tickcolor=t["rule"]),
        yaxis=dict(title=ytitle, gridcolor=t["grid"], linecolor=t["rule"], zeroline=False),
        legend=dict(orientation="h", yref="paper", y=1.02, x=0.0, xanchor="left", yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12)),
        showlegend=legend,
        hoverlabel=dict(bgcolor=t["paper"], font=dict(family=t["font"], color=t["ink"]), bordercolor=t["rule"]),
    )
    return fig


def hand(fig, theme, text, x, y, ax=40, ay=-40, xref="x", yref="y", xlog=False):
    """the examiner's red-pen remark with an arrow (xlog: the x axis is logarithmic)"""
    t = T(theme)
    if xlog:
        x = float(np.log10(x))
    fig.add_annotation(x=x, y=y, xref=xref, yref=yref, text=text, showarrow=True, ax=ax, ay=ay,
                       arrowhead=2, arrowwidth=1.8, arrowcolor=t["red"],
                       font=dict(family=t["hand"], size=t["hand_size"], color=t["red"]),
                       bgcolor="rgba(0,0,0,0)")


def log_ticks(fig, vals):
    cand = [10, 20, 30, 50, 100, 200, 300, 500, 1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000, 100000, 200000]
    lo, hi = float(np.nanmin(vals)) * 0.8, float(np.nanmax(vals)) * 1.25
    tv = [v for v in cand if lo <= v <= hi]
    fig.update_xaxes(type="log", tickvals=tv, ticktext=[f"{v // 1000}k" if v >= 1000 else str(v) for v in tv])


# ------------------------------------------------------------------ Q1
def agreement(theme, year, metric_keys=("papers", "citations")):
    t = T(theme)
    fig = base(theme, "Agreement between NIRF research score and OpenAlex output, by year",
               "NIRF ranking year", "Agreement (rank correlation, 0 to 1)")
    ci = D.agreement_main_ci("pubs_own")
    pap = D.agreement_by_year("pubs_own")
    cit = D.agreement_by_year("cites_received")
    if ci is not None and ci["ci_low"].notna().any():
        xs = list(ci.index) + list(ci.index[::-1])
        ys = list(ci.ci_high) + list(ci.ci_low[::-1])
        fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself", fillcolor="rgba(62,111,216,0.13)", mode="lines",
                                 line=dict(width=0), hoverinfo="skip", name="95% interval (papers)"))
    fig.add_trace(go.Scatter(x=cit.index, y=cit.values, mode="lines+markers", name="Citations received",
                             line=dict(color=t["a2"], width=2, dash="dash"),
                             marker=dict(symbol="square-open", size=9, color=t["a2"], line=dict(width=2)),
                             hovertemplate="%{x}: %{y:.2f}<extra>citations</extra>"))
    fig.add_trace(go.Scatter(x=pap.index, y=pap.values, mode="lines+markers", name="Papers",
                             line=dict(color=t["a"], width=3),
                             marker=dict(symbol="circle", size=9, color=t["a"]),
                             hovertemplate="%{x}: %{y:.2f}<extra>papers</extra>"))
    fig.update_yaxes(range=[0.5, 1.0], dtick=0.1)
    fig.update_xaxes(dtick=1)
    low_year = int(pap.idxmin())
    y = float(pap.loc[year])
    note = f"{y:.2f} in {year}" + (", weakest year!" if year == low_year else "")
    hand(fig, theme, note, year, y, ax=-30, ay=55)
    fig.add_vline(x=year, line=dict(color=t["red"], width=1, dash="dot"))
    return fig


def scatter_year(theme, year, metric):
    t = T(theme)
    m = D.METRICS[metric]
    g = D.J[D.J.year == year].copy()
    r = D.rho(g, "rpc", m["col"])
    fig = base(theme, f"Research score against {m['word']}, NIRF {year}  (rank correlation {r:.2f})",
               m["axis"], "NIRF research score (RPC, 0 to 100)", height=470)
    top, bot = g[g["rank"] <= 50], g[g["rank"] > 50]
    for sub, name, sym, col in [(top, "NIRF rank 1 to 50", "square-open", t["b"]),
                                (bot, "NIRF rank 51 to 100", "circle", t["a"])]:
        fig.add_trace(go.Scatter(
            x=sub[m["per_year"]], y=sub.rpc, mode="markers", name=name,
            marker=dict(symbol=sym, size=10, color=col, line=dict(width=2, color=col)),
            customdata=np.stack([sub.label, sub["rank"], sub[m["col"]]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>NIRF rank %{customdata[1]}<br>research score %{y:.1f}"
                          "<br>%{x:,.0f} per year<extra></extra>"))
    log_ticks(fig, g[m["per_year"]])
    gap = g.assign(a=g[m["gap"]].abs()).nlargest(2, "a")
    for k, (_, row) in enumerate(gap.iterrows()):
        hand(fig, theme, row.label, row[m["per_year"]], row.rpc, ax=(-70 if k == 0 else 60), ay=(-45 if k == 0 else 50), xlog=True)
    return fig


def split_halves(theme, metric, year):
    t = T(theme)
    m = D.METRICS[metric]
    top, bot = D.split_by_half(m["col"])
    fig = base(theme, f"Agreement in the top 50 and in ranks 51 to 100 ({m['word']})",
               "NIRF ranking year", "Agreement (rank correlation, 0 to 1)")
    fig.add_trace(go.Scatter(x=top.index, y=top.values, mode="lines+markers", name="NIRF rank 1 to 50",
                             line=dict(color=t["b"], width=2, dash="dash"),
                             marker=dict(symbol="square-open", size=10, color=t["b"], line=dict(width=2)),
                             hovertemplate="%{x}: %{y:.2f}<extra>rank 1-50</extra>"))
    fig.add_trace(go.Scatter(x=bot.index, y=bot.values, mode="lines+markers", name="NIRF rank 51 to 100",
                             line=dict(color=t["a"], width=3),
                             marker=dict(symbol="circle", size=10, color=t["a"]),
                             hovertemplate="%{x}: %{y:.2f}<extra>rank 51-100</extra>"))
    fig.update_yaxes(range=[0, 1.0], dtick=0.2)
    fig.update_xaxes(dtick=1)
    yb = float(bot.loc[year])
    hand(fig, theme, f"{yb:.2f} in {year}", year, yb, ax=-40, ay=50)
    return fig


# ------------------------------------------------------------------ Q2
def gaps(theme, year, metric, n=7):
    t = T(theme)
    m = D.METRICS[metric]
    g = D.J[D.J.year == year].copy()
    gap = m["gap"]
    sel = pd_concat(g.nsmallest(n, gap), g.nlargest(n, gap)).sort_values(gap)
    colors = [t["a"] if v < 0 else t["b"] for v in sel[gap]]
    fig = base(theme, f"Biggest rank gaps, NIRF {year}", "Rank gap in places (rank by " + m["word"] + " minus research-score rank)",
               None, height=520, legend=False)
    fig.add_trace(go.Bar(x=sel[gap], y=sel.label, orientation="h", marker=dict(color=colors, line=dict(width=0)),
                         customdata=np.stack([sel["rank"], sel.rpc, sel[m["col"]]], axis=-1),
                         hovertemplate="<b>%{y}</b><br>NIRF rank %{customdata[0]}<br>research score %{customdata[1]:.1f}"
                                       "<br>" + m["word"] + ": %{customdata[2]:,.0f} (3 years)<extra></extra>"))
    fig.update_yaxes(automargin=True, gridcolor="rgba(0,0,0,0)")
    fig.add_vline(x=0, line=dict(color=t["ink"], width=1.2))
    lim = max(abs(sel[gap])) * 1.7
    fig.update_xaxes(range=[-lim, lim])
    fig.add_annotation(xref="paper", yref="paper", x=0.0, y=1.0, yanchor="bottom", xanchor="left", showarrow=False,
                       text="Output ranks higher than the score", font=dict(color=t["a"], size=12))
    fig.add_annotation(xref="paper", yref="paper", x=1.0, y=1.0, yanchor="bottom", xanchor="right", showarrow=False,
                       text="Score ranks higher than the output", font=dict(color=t["b"], size=12))
    top = sel.iloc[0] if abs(sel.iloc[0][gap]) >= abs(sel.iloc[-1][gap]) else sel.iloc[-1]
    hand(fig, theme, f"{abs(int(top[gap]))} places!", top[gap], top.label,
         ax=(-70 if top[gap] < 0 else 70), ay=0)
    return fig


def pd_concat(a, b):
    import pandas as pd
    return pd.concat([a, b])


def slope(theme, year, metric, n=8):
    t = T(theme)
    m = D.METRICS[metric]
    g = D.J[D.J.year == year].copy()
    gap = m["gap"]
    hi = set(g.assign(a=g[gap].abs()).nlargest(n, "a").id_new)
    fig = base(theme, f"Research-score rank against rank by {m['word']}, NIRF {year}", None, None, height=620, legend=False)
    for _, r in g[~g.id_new.isin(hi)].iterrows():
        fig.add_trace(go.Scatter(x=[0, 1], y=[r.rank_rpc, r[m["rank"]]], mode="lines",
                                 line=dict(color=t["soft"], width=1), hoverinfo="skip", showlegend=False))
    sel = g[g.id_new.isin(hi)]
    ly = _spread({r.id_new: r.rank_rpc for _, r in sel.iterrows()}, 3.4)
    ry = _spread({r.id_new: r[m["rank"]] for _, r in sel.iterrows()}, 3.4)
    for _, r in sel.iterrows():
        up = r[m["rank"]] < r.rank_rpc
        col = t["a"] if up else t["b"]
        fig.add_trace(go.Scatter(x=[0, 1], y=[r.rank_rpc, r[m["rank"]]], mode="lines+markers",
                                 line=dict(color=col, width=2.5, dash="solid" if up else "dash"),
                                 marker=dict(size=7, symbol="circle" if up else "square-open", line=dict(width=2)),
                                 hovertemplate=f"<b>{r.label}</b><br>score rank {int(r.rank_rpc)}, rank by {m['word']} "
                                               f"{int(r[m['rank']])}<extra></extra>", showlegend=False))
        fig.add_annotation(x=0, y=ly[r.id_new], xanchor="right", xshift=-8, text=f"{r.label}  {int(r.rank_rpc)}",
                           showarrow=False, font=dict(size=11, color=col))
        fig.add_annotation(x=1, y=ry[r.id_new], xanchor="left", xshift=8, text=f"{int(r[m['rank']])}  {r.label}",
                           showarrow=False, font=dict(size=11, color=col))
    fig.update_yaxes(range=[100.5, 0.5], title="Rank within the year (1 = best)", tickvals=[1, 25, 50, 75, 100])
    fig.update_xaxes(range=[-0.55, 1.55], tickvals=[0, 1], ticktext=["NIRF research-score rank", "Rank by " + m["word"]],
                     gridcolor="rgba(0,0,0,0)", showline=False)
    fig.update_layout(margin=dict(l=70, r=30, t=58, b=54))
    return fig


def _spread(pos, gap):
    """push label positions apart so they do not overlap; pos = {key: rank}"""
    items = sorted(pos.items(), key=lambda kv: kv[1])
    out, last = {}, -1e9
    for k, v in items:
        v = max(v, last + gap)
        out[k] = v
        last = v
    return out


def by_type(theme, year, metric):
    t = T(theme)
    m = D.METRICS[metric]
    g = D.J[D.J.year == year].copy()
    gap = m["gap"]
    order = g.groupby("type")[gap].median().sort_values().index.tolist()
    fig = base(theme, f"Rank gap by type of institution, NIRF {year}",
               "Rank gap in places (rank by " + m["word"] + " minus research-score rank)", None, height=470, legend=False)
    rng = np.random.default_rng(3)
    pos = {ty: i for i, ty in enumerate(order)}
    for ty in order:
        s = g[g.type == ty]
        yy = pos[ty] + rng.uniform(-0.22, 0.22, len(s))
        fig.add_trace(go.Scatter(x=s[gap], y=yy, mode="markers",
                                 marker=dict(symbol="circle-open", size=9, color=t["a"], line=dict(width=1.8)),
                                 customdata=np.stack([s.label, s["rank"]], axis=-1),
                                 hovertemplate="<b>%{customdata[0]}</b><br>NIRF rank %{customdata[1]}<br>gap %{x} places<extra></extra>",
                                 showlegend=False))
        fig.add_trace(go.Scatter(x=[s[gap].median()], y=[pos[ty]], mode="markers",
                                 marker=dict(symbol="diamond", size=14, color=t["b"], line=dict(width=1.5, color=t["paper"])),
                                 hovertemplate=f"median {s[gap].median():.0f} places (n={len(s)})<extra>{ty}</extra>",
                                 showlegend=False))
    fig.add_vline(x=0, line=dict(color=t["ink"], width=1.2))
    fig.update_yaxes(tickvals=list(range(len(order))), ticktext=order, range=[-0.6, len(order) - 0.4], automargin=True, gridcolor=t["grid"])
    fig.add_annotation(xref="paper", yref="paper", x=0.0, y=1.0, yanchor="bottom", xanchor="left", showarrow=False,
                       text="Output ranks higher than the score", font=dict(color=t["a"], size=12))
    fig.add_annotation(xref="paper", yref="paper", x=1.0, y=1.0, yanchor="bottom", xanchor="right", showarrow=False,
                       text="Score ranks higher than the output", font=dict(color=t["b"], size=12))
    return fig


# ------------------------------------------------------------------ marksheet
def marksheet(theme, ids, metric):
    t = T(theme)
    m = D.METRICS[metric]
    fig = base(theme, "Rank by research score and rank by " + m["word"] + ", every year in the top 100",
               "NIRF ranking year", "Rank within the year (1 = best)", height=430)
    palettes = [(t["b"], t["a"]), ("#7A5A00", "#2E6B3F")] if theme == "revaluation" else [(t["b"], t["a"]), ("#7A5A00", "#2E6B3F")]
    for k, iid in enumerate(ids):
        s = D.J[D.J.id_new == iid].sort_values("year")
        if s.empty:
            continue
        c1, c2 = palettes[k % 2]
        nm = s.label.iloc[0]
        fig.add_trace(go.Scatter(x=s.year, y=s.rank_rpc, mode="lines+markers", name=f"{nm}: research-score rank",
                                 line=dict(color=c1, width=3), marker=dict(symbol="circle", size=9, color=c1),
                                 hovertemplate="%{x}: rank %{y}<extra>research score</extra>"))
        fig.add_trace(go.Scatter(x=s.year, y=s[m["rank"]], mode="lines+markers", name=f"{nm}: rank by {m['word']}",
                                 line=dict(color=c2, width=2, dash="dash"),
                                 marker=dict(symbol="square-open", size=9, color=c2, line=dict(width=2)),
                                 hovertemplate="%{x}: rank %{y}<extra>" + m["word"] + "</extra>"))
    fig.update_yaxes(range=[102, 0], tickvals=[1, 25, 50, 75, 100])
    fig.update_xaxes(dtick=1, range=[2016.6, 2025.4])
    fig.update_layout(legend=dict(orientation="h", y=-0.22, x=0, xanchor="left", yanchor="top"))
    return fig


# ------------------------------------------------------------------ Q3
def robustness(theme):
    t = T(theme)
    tab = D.robustness_table()
    fig = base(theme, "Does the answer survive different choices? Agreement with papers, by year",
               "NIRF ranking year", "Agreement (rank correlation, 0 to 1)", height=440)
    styles = [
        ("Main (own count, 3-year window)", t["a"], 3, "solid", "circle"),
        ("Lineage count", t["a2"], 2, "dash", "square-open"),
        ("Flagged institutions removed", t["b"], 2, "dot", "diamond-open"),
        ("Window shifted back one year", t["muted"], 2, "dashdot", "x"),
    ]
    for col, c, w, dash, sym in styles:
        fig.add_trace(go.Scatter(x=tab.index, y=tab[col], mode="lines+markers", name=col,
                                 line=dict(color=c, width=w, dash=dash),
                                 marker=dict(symbol=sym, size=9, color=c, line=dict(width=2)),
                                 hovertemplate="%{x}: %{y:.2f}<extra>" + col + "</extra>"))
    fig.update_yaxes(range=[0.5, 1.0], dtick=0.1)
    fig.update_xaxes(dtick=1)
    fig.update_layout(legend=dict(orientation="h", y=-0.25, x=0, xanchor="left", yanchor="top"))
    return fig


# ------------------------------------------------------------------ cleaning
def before_after_counts(theme):
    t = T(theme)
    raw_ids, raw_names, raw_locs = 342, 231, 106
    after_ids = D.J.id_new.nunique(); after_names = after_ids; after_locs = D.J.location_clean.nunique()
    if D.LOG is not None:
        try:
            lg = D.LOG.set_index("step")
            raw_ids = int(lg.loc["distinct NIRF ids in the raw scrape", "count"])
            raw_names = int(lg.loc["distinct institution name strings", "count"])
            raw_locs = int(lg.loc["distinct location strings", "count"])
        except Exception:
            pass
    cats = ["Institution ids", "Name spellings", "Location spellings"]
    before, after = [raw_ids, raw_names, raw_locs], [after_ids, after_names, after_locs]
    fig = base(theme, "Cleaning: distinct labels before and after", "Distinct values (count)", None, height=300)
    fig.add_trace(go.Bar(y=cats, x=before, orientation="h", name="Before cleaning", marker=dict(color=t["soft"]),
                         text=before, textposition="outside", cliponaxis=False))
    fig.add_trace(go.Bar(y=cats, x=after, orientation="h", name="After cleaning", marker=dict(color=t["a"]),
                         text=after, textposition="outside", cliponaxis=False))
    fig.update_layout(barmode="group", bargap=0.35)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(range=[0, max(before) * 1.15])
    return fig, (before, after)


def lineage_vs_own(theme, year=2025):
    t = T(theme)
    g = D.J[(D.J.year == year) & D.J.flag_lineage_inflated].sort_values("lineage_ratio")
    fig = base(theme, f"Cleaning: papers counted per institution before (lineage) and after (own), window for NIRF {year}",
               "Papers in the 3-year window", None, height=60 + 38 * max(len(g), 3), legend=True)
    for _, r in g.iterrows():
        fig.add_trace(go.Scatter(x=[r.pubs_own, r.pubs_lineage], y=[r.label, r.label], mode="lines",
                                 line=dict(color=t["rule"], width=2), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=g.pubs_lineage, y=g.label, mode="markers", name="Before: lineage count",
                             marker=dict(symbol="square-open", size=10, color=t["a2"], line=dict(width=2))))
    fig.add_trace(go.Scatter(x=g.pubs_own, y=g.label, mode="markers", name="After: own count",
                             marker=dict(symbol="circle", size=10, color=t["a"])))
    fig.update_yaxes(automargin=True)
    return fig


def outliers_plot(theme):
    t = T(theme)
    fig = base(theme, "Outlier check: papers per year against research score, all years pooled",
               "Papers per year, 3 years before the ranking (log scale)", "NIRF research score (RPC, 0 to 100)", height=430)
    fig.add_trace(go.Scatter(x=D.J.papers_per_year, y=D.J.rpc, mode="markers", name="Institution-year",
                             marker=dict(symbol="circle", size=6, color=t["soft"]),
                             customdata=np.stack([D.J.label, D.J.year], axis=-1),
                             hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{x:,.0f} papers/year<extra></extra>"))
    if D.OUT is not None and len(D.OUT):
        o = D.OUT.merge(D.J[["id_new", "year", "papers_per_year", "label"]], on=["id_new", "year"], how="left")
        fig.add_trace(go.Scatter(x=o.papers_per_year, y=o.rpc, mode="markers", name="Flagged by a test",
                                 marker=dict(symbol="circle-open", size=14, color=t["red"], line=dict(width=2.5)),
                                 customdata=np.stack([o.label, o.year, o.methods], axis=-1),
                                 hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
        hand(fig, theme, "small specialist institutes, kept", o.papers_per_year.min(), o.loc[o.papers_per_year.idxmin(), "rpc"], ax=110, ay=-60, xlog=True)
    log_ticks(fig, D.J.papers_per_year)
    return fig


def dropout_plot(theme):
    t = T(theme)
    drop, stay = D.dropout_stats()
    fig = base(theme, "Who leaves the top 100? Average NIRF rank in the year before", "Average NIRF rank (1 = best)", None, height=240, legend=False)
    fig.add_trace(go.Bar(y=["Stay in the next year", "Vanish the next year"], x=[stay.mean(), drop.mean()], orientation="h",
                         marker=dict(color=[t["a"], t["b"]]), text=[f"{stay.mean():.0f}  (n={len(stay)})", f"{drop.mean():.0f}  (n={len(drop)})"],
                         textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig
