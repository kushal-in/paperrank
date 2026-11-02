"""charts.py - every figure in the dashboard. Palette is retro print: paper, ink, rust, mustard, teal."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import data as D

PAPER, CREAM, INK = "#FFFFFF", "#FFFFFF", "#1A1A1A"
RUST, MUSTARD, TEAL, SAGE = "#C65D3B", "#E3A72F", "#2E7D7A", "#93A97A"
ROSE, NAVY, PLUM, TAUPE = "#E2A793", "#34506B", "#7A4B66", "#9A8878"
GRID = "#E6E6E0"
FONT = "'Libre Franklin', 'Helvetica Neue', Arial, sans-serif"
DISPLAY = "'Libre Franklin', 'Helvetica Neue', Arial, sans-serif"

# Okabe-Ito colour-blind-safe palette (lecture 8). Used when "All types" is chosen in the Colour control.
TYPE_COL_ALL = {"IIT": "#0072B2", "NIT and IIIT": "#E69F00", "Science institutes": "#CC79A7", "Medical": "#D55E00",
                "Agriculture": "#009E73", "Management": "#56B4E9", "Private and deemed": "#F0E442", "Public universities": "#7F7F7F"}
GREY = "#B9B9B2"
TYPE_COL = dict(TYPE_COL_ALL)


def set_highlight(hl):
    """one highlight colour and grey for the rest (lectures 6 and 8); hl = a type name, or 'all' for every colour"""
    for t in TYPE_COL_ALL:
        TYPE_COL[t] = TYPE_COL_ALL[t] if hl in (None, "all") else (RUST if t == hl else GREY)
TYPE_SYM = {"IIT": "circle", "NIT and IIIT": "square", "Science institutes": "diamond", "Medical": "triangle-up",
            "Agriculture": "cross", "Management": "star", "Private and deemed": "hexagon", "Public universities": "x"}
TYPE_SYM3D = {"IIT": "circle", "NIT and IIIT": "square", "Science institutes": "diamond", "Medical": "cross",
              "Agriculture": "x", "Management": "circle-open", "Private and deemed": "square-open",
              "Public universities": "diamond-open"}
TYPES = D.TYPES
SEQ = ["#FBF1D6", "#EBCB73", "#DC9446", "#B5533A", "#6B2E3A"]       # light -> dark, greyscale safe
DIV = [[0, TEAL], [0.5, "#F2F2EE"], [1, RUST]]
BAND_COL = ["#34506B", "#2E7D7A", "#93A97A", "#E3A72F", "#C65D3B"]
BANDS = [(1, 10, "1 to 10"), (11, 25, "11 to 25"), (26, 50, "26 to 50"), (51, 75, "51 to 75"), (76, 999, "76 to 100")]


def band(r):
    for lo, hi, lab in BANDS:
        if lo <= r <= hi:
            return lab
    return BANDS[-1][2]


def rgba(hexc, a):
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def base(fig, h=420, legend=True, top=18):
    fig.update_layout(
        height=h, margin=dict(l=62, r=22, t=top, b=56), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK), showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        hoverlabel=dict(bgcolor=CREAM, bordercolor=INK, font=dict(family=FONT, size=13, color=INK)),
        colorway=[NAVY, RUST, TEAL, MUSTARD, PLUM, SAGE])
    fig.update_xaxes(gridcolor=GRID, linecolor=INK, zeroline=False, ticks="outside", tickcolor=INK)
    fig.update_yaxes(gridcolor=GRID, linecolor=INK, zeroline=False, ticks="outside", tickcolor=INK)
    return fig


def logticks(lo, hi):
    vals = [v for v in [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
            if 10 ** lo <= v <= 10 ** hi]
    txt = [f"{v // 1000}k" if v >= 1000 else str(v) for v in vals]
    return [np.log10(v) for v in vals], txt


def _sub(df, types):
    return df[df.type.isin(types)] if types else df


def metric_cols(metric):
    m = D.METRICS[metric]
    return m["per_year"], m["rank"], m["gap"], m["word"], m["axis"]


# ----------------------------------------------------------------------------------- 3D hero
def hero3d(year, types):
    df = _sub(D.J[D.J.year == year], types)
    fig = go.Figure()
    for t in TYPES:
        g = df[df.type == t]
        if g.empty:
            continue
        fig.add_trace(go.Scatter3d(
            x=np.log10(g.papers_per_year), y=np.log10(g.cites_per_year), z=g.rpc, mode="markers", name=t,
            marker=dict(size=6.5, color=TYPE_COL[t], symbol=TYPE_SYM3D[t], opacity=0.95,
                        line=dict(color=INK, width=1)),
            text=g.name, customdata=np.c_[g.papers_per_year.round(0), g.cites_per_year.round(0), g["rank"]],
            hovertemplate="<b>%{text}</b><br>NIRF rank %{customdata[2]}<br>Research score %{z:.1f}<br>"
                          "%{customdata[0]:,.0f} papers/yr<br>%{customdata[1]:,.0f} citations/yr<extra></extra>"))
    tx, tt = logticks(1.2, 4.6)
    ty, tyt = logticks(2.0, 6.0)
    ax = dict(backgroundcolor=CREAM, gridcolor=GRID, zerolinecolor=GRID, showbackground=True, linecolor=INK,
              color=INK)
    fig.update_layout(scene=dict(
        xaxis=dict(title="Papers per year", tickvals=tx, ticktext=tt, range=[np.log10(df.papers_per_year.min()) - .1, np.log10(df.papers_per_year.max()) + .1], **ax),
        yaxis=dict(title="Citations per year", tickvals=ty, ticktext=tyt, range=[np.log10(df.cites_per_year.min()) - .1, np.log10(df.cites_per_year.max()) + .1], **ax),
        zaxis=dict(title="Research score (0 to 100)", range=[0, 100], **ax),
        camera=dict(eye=dict(x=1.7, y=-1.7, z=0.9)), aspectmode="manual", aspectratio=dict(x=1.2, y=1.2, z=0.9)))
    base(fig, 520, True, 0)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend=dict(y=1.0, yanchor="bottom", x=0))
    return fig


# ----------------------------------------------------------------------------------- animated
def race(types, metric):
    per, rk, gp, word, axis = metric_cols(metric)
    frames, first = [], None
    for y in D.YEARS:
        g = _sub(D.J[D.J.year == y], types).nsmallest(12, "rank")
        slots = [12 - i for i in range(len(g))]
        tr = go.Bar(x=g.rpc, y=slots, orientation="h", marker=dict(color=[TYPE_COL[t] for t in g.type], line=dict(color=INK, width=1.2)),
                    text=[f"{l}  {v:.1f}" for l, v in zip(g.label, g.rpc)], textposition="outside", cliponaxis=False,
                    textfont=dict(size=12, color=INK), customdata=np.c_[g.name, g[per].round(0)],
                    hovertemplate="%{customdata[0]}<br>research score %{x:.1f}<br>%{customdata[1]:,.0f} " + word + "/yr<extra></extra>")
        frames.append(go.Frame(data=[tr], name=str(y)))
        if first is None:
            first = tr
    fig = go.Figure(data=[first], frames=frames)
    _player(fig, [str(y) for y in D.YEARS], "Year: ", slider_y=-0.22, button_y=-0.52)
    base(fig, 600, False, 10)
    fig.update_xaxes(range=[0, 150], tickvals=[0, 20, 40, 60, 80, 100], title="NIRF research score (0 to 100)", fixedrange=True)
    fig.update_yaxes(range=[0.4, 12.9], showticklabels=False, showgrid=False, title="Top 12 in each year, best at the top", fixedrange=True)
    fig.update_layout(margin=dict(l=40, r=20, t=10, b=200))
    return fig


def anim_scatter(types, metric):
    per, rk, gp, word, axis = metric_cols(metric)
    xs = D.J[per]
    lo, hi = np.log10(xs.min()) - 0.08, np.log10(xs.max()) + 0.08
    frames, first = [], None
    for y in D.YEARS:
        g = D.J[D.J.year == y]
        traces = []
        for t in TYPES:
            gt = g[g.type == t] if (not types or t in types) else g.iloc[0:0]
            traces.append(go.Scatter(
                x=gt[per], y=gt.rpc, mode="markers", name=t, text=gt.name,
                marker=dict(size=11, color=TYPE_COL[t], symbol=TYPE_SYM[t], line=dict(color=INK, width=1), opacity=0.92),
                hovertemplate="<b>%{text}</b><br>%{x:,.0f} " + word + "/yr<br>research score %{y:.1f}<extra></extra>"))
        frames.append(go.Frame(data=traces, name=str(y)))
        if first is None:
            first = traces
    fig = go.Figure(data=first, frames=frames)
    _player(fig, [str(y) for y in D.YEARS], "Year: ")
    base(fig, 500, True)
    tv, tt = logticks(lo, hi)
    fig.update_xaxes(type="log", range=[lo, hi], title=axis)
    fig.update_yaxes(range=[0, 100], title="NIRF research score (0 to 100)")
    fig.update_layout(margin=dict(l=62, r=22, t=44, b=200))
    return fig


def _player(fig, names, prefix, slider_y=-0.22, button_y=-0.52):
    """play and pause on one row, the year slider on its own row above them; axes stay fixed, bars and points glide"""
    fig.update_layout(
        updatemenus=[dict(type="buttons", direction="left", x=0.0, y=button_y, xanchor="left", yanchor="top",
                          pad=dict(t=0, r=8), bgcolor="#FFFFFF", bordercolor=INK, borderwidth=1.5,
                          font=dict(family=FONT, size=13, color=INK),
                          buttons=[dict(label="Play", method="animate",
                                        args=[None, dict(frame=dict(duration=1300, redraw=False), fromcurrent=True,
                                                         transition=dict(duration=900, easing="cubic-in-out"))]),
                                   dict(label="Pause", method="animate",
                                        args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate",
                                                           transition=dict(duration=0))])])],
        sliders=[dict(active=0, x=0.0, len=1.0, y=slider_y, yanchor="top", pad=dict(t=0, b=0, l=0, r=0),
                      bgcolor=GRID, bordercolor=INK, tickcolor=INK, activebgcolor=MUSTARD,
                      font=dict(family=FONT, size=12, color=INK),
                      currentvalue=dict(prefix=prefix, font=dict(family=FONT, size=15, color=INK), xanchor="left"),
                      steps=[dict(label=n, method="animate",
                                  args=[[n], dict(mode="immediate", frame=dict(duration=0, redraw=False),
                                                  transition=dict(duration=600, easing="cubic-in-out"))]) for n in names])])


# ----------------------------------------------------------------------------------- correlation
def corr_line():
    fig = go.Figure()
    if D.SP is None:
        return base(fig, 380)
    spec = [("pubs_own", "Papers", NAVY, "circle", "solid"), ("cites_received", "Citations", RUST, "square", "dash")]
    for col, nm, c, sym, dash in spec:
        s = D.SP[(D.SP.spec == "main") & (D.SP.metric == col)].sort_values("year")
        fig.add_trace(go.Scatter(x=list(s.year) + list(s.year[::-1]), y=list(s.ci_high) + list(s.ci_low[::-1]),
                                 fill="toself", fillcolor=rgba(c, 0.16), line=dict(width=0), mode="lines",
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=s.year, y=s.spearman, mode="lines+markers", name=nm,
                                 line=dict(color=c, width=3, dash=dash), marker=dict(size=10, symbol=sym,
                                 color=c if sym == "circle" else CREAM, line=dict(color=c, width=2)),
                                 hovertemplate=f"{nm}<br>%{{x}}: %{{y:.2f}}<extra></extra>"))
    s = D.SP[(D.SP.spec == "overall_rank_control")].sort_values("year")
    fig.add_trace(go.Scatter(x=s.year, y=s.spearman, mode="lines", name="Overall rank vs papers (control)",
                             line=dict(color=TAUPE, width=2, dash="dot")))
    base(fig, 400, True, 44)
    fig.update_xaxes(title="NIRF ranking year", dtick=1)
    fig.update_yaxes(title="Rank correlation (Spearman, 0 to 1)", range=[0, 1.02])
    return fig


def robust_heat():
    t = D.robustness_table().T
    t.index = ["Main: own count", "Lineage count", "Flagged removed", "Window shifted 1 year"]
    z = t.values
    fig = go.Figure(go.Heatmap(z=z, x=[str(c) for c in t.columns], y=list(t.index), colorscale=SEQ, zmin=0.2, zmax=1,
                               xgap=3, ygap=3, text=np.round(z, 2), texttemplate="%{text}", textfont=dict(size=13),
                               colorbar=dict(title="Spearman", thickness=12, len=0.8, outlinecolor=INK, outlinewidth=1),
                               hovertemplate="%{y}<br>%{x}: %{z:.2f}<extra></extra>"))
    base(fig, 330, False, 10)
    fig.update_layout(margin=dict(l=150, r=20, t=10, b=50))
    fig.update_xaxes(title="NIRF ranking year", side="bottom")
    fig.update_yaxes(autorange="reversed")
    return fig


# ----------------------------------------------------------------------------------- flows
def sankey_bands(year, types, metric):
    per, rk, gp, word, axis = metric_cols(metric)
    g = _sub(D.J[D.J.year == year], types).copy()
    g["a"] = g.rank_rpc.map(band)
    g["b"] = g[rk].map(band)
    labs = [b[2] for b in BANDS]
    ct = pd.crosstab(g.a, g.b).reindex(index=labs, columns=labs, fill_value=0)
    src, tgt, val, col = [], [], [], []
    for i, a in enumerate(labs):
        for j, b in enumerate(labs):
            if ct.loc[a, b]:
                src.append(i); tgt.append(5 + j); val.append(int(ct.loc[a, b]))
                col.append(rgba(BAND_COL[i], 0.45))
    fig = go.Figure(go.Sankey(
        arrangement="snap", node=dict(pad=22, thickness=22, line=dict(color=INK, width=1.5),
                                      label=[f"Score rank {b}" for b in labs] + [f"{word.title()} rank {b}" for b in labs],
                                      color=BAND_COL + BAND_COL, hovertemplate="%{label}: %{value} institutions<extra></extra>"),
        link=dict(source=src, target=tgt, value=val, color=col,
                  hovertemplate="%{value} institutions<br>%{source.label}<br>to %{target.label}<extra></extra>")))
    base(fig, 470, False, 10)
    fig.update_layout(font=dict(size=13, family=FONT, color=INK))
    stay = int(sum(ct.loc[a, a] for a in labs if a in ct.index))
    return fig, stay, len(g)


def sankey_years(types):
    yrs = [2017, 2019, 2021, 2023, 2025]
    labs = ["Top 10", "11 to 30", "31 to 60", "61 to 100", "Not listed"]

    def bd(r):
        if pd.isna(r): return 4
        return 0 if r <= 10 else 1 if r <= 30 else 2 if r <= 60 else 3
    ids = D.J[D.J.type.isin(types)].id_new.unique() if types else D.J.id_new.unique()
    pv = D.J[D.J.id_new.isin(ids)].pivot(index="id_new", columns="year", values="rank").reindex(columns=yrs)
    pv = pv[pv.notna().any(axis=1)]
    nid = lambda yi, b: yi * 5 + b
    src, tgt, val, col = [], [], [], []
    for yi in range(len(yrs) - 1):
        a = pv[yrs[yi]].map(bd); b = pv[yrs[yi + 1]].map(bd)
        ct = pd.crosstab(a, b)
        for i in ct.index:
            for j in ct.columns:
                if ct.loc[i, j] and not (i == 4 and j == 4):
                    src.append(nid(yi, i)); tgt.append(nid(yi + 1, j)); val.append(int(ct.loc[i, j]))
                    col.append(rgba(BAND_COL[i], 0.42))
    xs = [yi / (len(yrs) - 1) * 0.98 + 0.01 for yi in range(len(yrs)) for _ in range(5)]
    fig = go.Figure(go.Sankey(
        arrangement="snap", node=dict(pad=14, thickness=18, line=dict(color=INK, width=1.2),
                                      label=[labs[b] if yi == 0 else "" for yi in range(len(yrs)) for b in range(5)],
                                      color=[BAND_COL[b] for _ in yrs for b in range(5)], x=xs,
                                      y=[0.02 + b * 0.2 for _ in yrs for b in range(5)]),
        link=dict(source=src, target=tgt, value=val, color=col,
                  hovertemplate="%{value} institutions<br>%{source.label} to %{target.label}<extra></extra>")))
    for yi, y in enumerate(yrs):
        fig.add_annotation(x=yi / (len(yrs) - 1) * 0.98 + 0.01, y=1.06, xref="paper", yref="paper", text=f"<b>{y}</b>",
                           showarrow=False, font=dict(family=DISPLAY, size=16, color=INK))
    base(fig, 480, False, 40)
    moved = int(((pv[2017].map(bd) != pv[2025].map(bd))).sum())
    return fig, moved, len(pv)


# ----------------------------------------------------------------------------------- composition
def treemap(year, types, metric):
    per, rk, gp, word, axis = metric_cols(metric)
    g = _sub(D.J[D.J.year == year], types)
    fig = go.Figure(go.Treemap(
        labels=list(g.label) + list(g.type.unique()), parents=list(g.type) + [""] * g.type.nunique(),
        values=list(g[per].round(0)) + [0] * g.type.nunique(), branchvalues="remainder",
        marker=dict(colors=list(g[gp]) + [CREAM] * g.type.nunique(), colorscale=DIV, cmid=0,
                    cmin=-40, cmax=40, line=dict(color=INK, width=1.5),
                    colorbar=dict(title="Rank gap", thickness=12, len=0.8, outlinecolor=INK, outlinewidth=1)),
        textfont=dict(family=FONT, size=13, color=INK), pathbar=dict(visible=False), tiling=dict(pad=3), root_color=CREAM,
        customdata=np.c_[list(g[gp]) + [0] * g.type.nunique()],
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} " + word + "/yr<br>rank gap %{customdata[0]:+.0f}<extra></extra>"))
    base(fig, 470, False, 8)
    fig.update_layout(margin=dict(l=4, r=4, t=8, b=4))
    return fig


def sunburst(year, types):
    g = _sub(D.J[D.J.year == year], types).copy()
    g["band"] = g["rank"].map(band)
    ids, labels, parents, values, colors = [], [], [], [], []
    for t, gt in g.groupby("type"):
        ids.append(t); labels.append(t); parents.append(""); values.append(len(gt)); colors.append(TYPE_COL[t])
        for b, gb in gt.groupby("band"):
            ids.append(f"{t}|{b}"); labels.append(b); parents.append(t); values.append(len(gb))
            colors.append(rgba(TYPE_COL[t], 0.55))
    fig = go.Figure(go.Sunburst(ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
                                marker=dict(colors=colors, line=dict(color=INK, width=1.5)),
                                insidetextorientation="radial", textfont=dict(family=FONT, size=13, color=INK),
                                hovertemplate="%{label}: %{value} institutions<extra></extra>"))
    base(fig, 470, False, 8)
    fig.update_layout(margin=dict(l=4, r=4, t=8, b=4))
    return fig


def parcoords(year, types):
    g = _sub(D.J[D.J.year == year], types)
    dims = [dict(label="Teaching", values=g.tlr), dict(label="Research", values=g.rpc), dict(label="Graduation", values=g.go),
            dict(label="Outreach", values=g.oi), dict(label="Perception", values=g.pr),
            dict(label="Papers/yr (log)", values=np.log10(g.papers_per_year),
                 tickvals=logticks(1.3, 4.5)[0], ticktext=logticks(1.3, 4.5)[1]),
            dict(label="Citations/yr (log)", values=np.log10(g.cites_per_year),
                 tickvals=logticks(2, 6)[0], ticktext=logticks(2, 6)[1])]
    fig = go.Figure(go.Parcoords(line=dict(color=g["rank"], colorscale=SEQ[::-1], showscale=True,
                                           colorbar=dict(title="NIRF rank", thickness=12, len=0.8)),
                                 dimensions=dims, labelfont=dict(family=FONT, size=13, color=INK),
                                 tickfont=dict(family=FONT, size=11, color=INK), rangefont=dict(size=10, color=INK)))
    base(fig, 460, False, 60)
    fig.update_layout(margin=dict(l=50, r=60, t=90, b=30))
    return fig


# ----------------------------------------------------------------------------------- distributions
def violin_type(year, types, col="rpc", title="NIRF research score (0 to 100)"):
    g = _sub(D.J[D.J.year == year], types)
    fig = go.Figure()
    for t in TYPES:
        gt = g[g.type == t]
        if gt.empty:
            continue
        fig.add_trace(go.Violin(x=gt[col], y=[t] * len(gt), orientation="h", name=t, side="positive", width=1.6,
                                points="all", pointpos=-0.35, jitter=0.25, meanline_visible=True,
                                line=dict(color=INK, width=1.3), fillcolor=rgba(TYPE_COL[t], 0.55),
                                marker=dict(color=TYPE_COL[t], size=6, symbol=TYPE_SYM[t], line=dict(color=INK, width=0.8)),
                                text=gt.name, hovertemplate="%{text}<br>%{x:.1f}<extra></extra>", spanmode="hard"))
    base(fig, 440, False, 10)
    fig.update_layout(margin=dict(l=150, r=20, t=10, b=56))
    fig.update_xaxes(title=title)
    fig.update_yaxes(autorange="reversed")
    return fig


def surface3d():
    j = D.J
    x = np.log10(j.papers_per_year.values); y = j.rpc.values
    xb = np.linspace(1.2, 4.2, 46); yb = np.linspace(0, 100, 46)
    H, _, _ = np.histogram2d(x, y, bins=[xb, yb])
    k = np.exp(-0.5 * (np.arange(-4, 5) / 1.6) ** 2); k /= k.sum()
    for ax in (0, 1):
        H = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), ax, H)
    xc = (xb[:-1] + xb[1:]) / 2; yc = (yb[:-1] + yb[1:]) / 2
    fig = go.Figure(go.Surface(x=xc, y=yc, z=H.T, colorscale=SEQ, showscale=False, opacity=0.97,
                               contours=dict(z=dict(show=True, usecolormap=False, color=INK, width=2, project_z=False)),
                               lighting=dict(ambient=0.8, diffuse=0.6, specular=0.2),
                               hovertemplate="papers/yr 10^%{x:.1f}<br>score %{y:.0f}<br>density %{z:.1f}<extra></extra>"))
    tx, tt = logticks(1.3, 4.1)
    ax = dict(backgroundcolor=CREAM, gridcolor=GRID, showbackground=True, color=INK)
    fig.update_layout(scene=dict(xaxis=dict(title="Papers per year", tickvals=tx, ticktext=tt, **ax),
                                 yaxis=dict(title="Research score", **ax), zaxis=dict(title="Institution-years", **ax),
                                 camera=dict(eye=dict(x=1.6, y=-1.6, z=0.8)), aspectratio=dict(x=1.2, y=1.1, z=0.6)))
    base(fig, 460, False, 0)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


# ----------------------------------------------------------------------------------- institutions
def radar(ida, idb, year):
    cats = ["Teaching", "Research", "Graduation", "Outreach", "Perception", "Papers (percentile)"]
    fig = go.Figure()
    y = D.J[D.J.year == year]
    pct = y.pubs_own.rank(pct=True) * 100
    for idx, (iid, c, dash) in enumerate([(ida, NAVY, "solid"), (idb, RUST, "dash")]):
        r = y[y.id_new == iid]
        if r.empty:
            continue
        r = r.iloc[0]
        v = [r.tlr, r.rpc, r.go, r.oi, r.pr, float(pct[r.name])]
        fig.add_trace(go.Scatterpolar(r=v + v[:1], theta=cats + cats[:1], name=r["label"], fill="toself",
                                      fillcolor=rgba(c, 0.22), line=dict(color=c, width=3, dash=dash),
                                      marker=dict(size=8, symbol="circle" if idx == 0 else "square"),
                                      hovertemplate="%{theta}: %{r:.1f}<extra>" + r["label"] + "</extra>"))
    base(fig, 440, True, 30)
    fig.update_layout(polar=dict(bgcolor=CREAM, radialaxis=dict(range=[0, 100], gridcolor=GRID, linecolor=INK,
                                                                 tickfont=dict(size=10)),
                                 angularaxis=dict(gridcolor=GRID, linecolor=INK, tickfont=dict(size=13))),
                      margin=dict(l=70, r=70, t=50, b=30))
    return fig


def trajectory(iid):
    g = D.history(iid)
    fig = go.Figure()
    spec = [("rank", "NIRF overall rank", INK, "circle", "solid"), ("rank_rpc", "Rank by research score", TEAL, "square", "dash"),
            ("rank_pubs_own", "Rank by papers", RUST, "diamond", "dot"), ("rank_cites_received", "Rank by citations", MUSTARD, "triangle-up", "dashdot")]
    for col, nm, c, sym, dash in spec:
        fig.add_trace(go.Scatter(x=g.year, y=g[col], mode="lines+markers", name=nm, line=dict(color=c, width=3, dash=dash),
                                 marker=dict(size=10, symbol=sym, color=c if sym == "circle" else CREAM, line=dict(color=c, width=2)),
                                 hovertemplate=nm + "<br>%{x}: rank %{y:.0f}<extra></extra>"))
    base(fig, 400, True, 44)
    fig.update_xaxes(title="NIRF ranking year", dtick=1, range=[2016.6, 2025.4])
    fig.update_yaxes(title="Rank within that year's top 100 (1 = best)", range=[float(np.nanmax(g[["rank", "rank_rpc", "rank_pubs_own", "rank_cites_received"]].values)) + 3, 0.5])
    return fig


def bump(types):
    j = D.J[D.J.type.isin(types)] if types else D.J
    top = j[j.year == 2025].nsmallest(12, "rank").id_new
    g = j[j.id_new.isin(top)]
    fig = go.Figure()
    for iid, gi in g.groupby("id_new"):
        gi = gi.sort_values("year"); t = gi.type.iloc[0]
        fig.add_trace(go.Scatter(x=gi.year, y=gi["rank"], mode="lines+markers", name=gi.label.iloc[0], showlegend=False,
                                 line=dict(color=TYPE_COL[t], width=4, shape="spline", smoothing=0.6),
                                 marker=dict(size=11, color=CREAM, symbol=TYPE_SYM[t], line=dict(color=TYPE_COL[t], width=2.5)),
                                 hovertemplate=gi.label.iloc[0] + "<br>%{x}: rank %{y}<extra></extra>"))
        last = gi.iloc[-1]
        fig.add_annotation(x=last.year, y=last["rank"], text=" " + last.label, xanchor="left", showarrow=False,
                           font=dict(size=12, color=INK))
    base(fig, 460, False, 10)
    fig.update_layout(margin=dict(l=60, r=210, t=10, b=56))
    fig.update_xaxes(title="NIRF ranking year", dtick=1, range=[2016.7, 2025.3])
    fig.update_yaxes(title="NIRF overall rank (1 = best)", range=[g["rank"].max() + 1.5, 0])
    return fig


def rank_heat(types):
    j = D.J[D.J.type.isin(types)] if types else D.J
    pv = j.pivot_table(index="label", columns="year", values="rank")
    pv = pv.loc[pv.mean(axis=1).sort_values().index[:30]]
    fig = go.Figure(go.Heatmap(z=pv.values, x=[str(c) for c in pv.columns], y=list(pv.index), xgap=3, ygap=3,
                               colorscale=SEQ[::-1], zmin=1, zmax=100, text=np.where(np.isnan(pv.values), "", np.nan_to_num(np.round(pv.values)).astype(int).astype(str)), texttemplate="%{text}",
                               textfont=dict(size=11), colorbar=dict(title="Rank", thickness=12, len=0.8),
                               hovertemplate="%{y}<br>%{x}: rank %{z:.0f}<extra></extra>"))
    base(fig, 640, False, 10)
    fig.update_layout(margin=dict(l=230, r=20, t=10, b=50))
    fig.update_xaxes(title="NIRF ranking year", side="bottom")
    fig.update_yaxes(autorange="reversed")
    return fig


# ----------------------------------------------------------------------------------- gaps
def lollipop(year, types, metric):
    per, rk, gp, word, axis = metric_cols(metric)
    g = _sub(D.J[D.J.year == year], types)
    top = pd.concat([g.nlargest(9, gp), g.nsmallest(9, gp)]).sort_values(gp)
    fig = go.Figure()
    lim = max(abs(top[gp]).max(), 5) * 1.35
    for _, r in top.iterrows():
        c = RUST if r[gp] > 0 else TEAL
        fig.add_trace(go.Scatter(x=[0, r[gp]], y=[r["label"]] * 2, mode="lines", line=dict(color=c, width=3), hoverinfo="skip", showlegend=False))
    pos, neg = top[top[gp] > 0], top[top[gp] <= 0]
    for d, c, sym, nm in [(pos, RUST, "circle", f"Score ranks higher than {word}"), (neg, TEAL, "diamond", f"{word.title()} rank higher than score")]:
        fig.add_trace(go.Scatter(x=d[gp], y=d["label"], mode="markers+text", name=nm, text=[f"{v:+.0f}" for v in d[gp]],
                                 textposition=["middle right" if v > 0 else "middle left" for v in d[gp]],
                                 marker=dict(size=15, color=c, symbol=sym, line=dict(color=INK, width=1.5)),
                                 customdata=np.c_[d["rank_rpc"], d[rk]],
                                 hovertemplate="<b>%{y}</b><br>score rank %{customdata[0]:.0f}, " + word + " rank %{customdata[1]:.0f}<extra></extra>"))
    base(fig, 540, True, 40)
    fig.update_layout(margin=dict(l=230, r=30, t=44, b=56))
    fig.update_xaxes(range=[-lim, lim], title=f"Rank gap: {word} rank minus research-score rank (places)")
    fig.update_yaxes(showgrid=False)
    return fig


def dropouts():
    leave, stay = D.dropout_stats()
    labs = [b[2] for b in BANDS]
    f = lambda s: s.map(band).value_counts().reindex(labs, fill_value=0)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labs, y=f(stay), name="Stayed in the top 100", marker=dict(color=SAGE, line=dict(color=INK, width=1.3))))
    fig.add_trace(go.Bar(x=labs, y=f(leave), name="Left the next year", marker=dict(color=RUST, pattern=dict(shape="/", fgcolor=INK, size=6), line=dict(color=INK, width=1.3))))
    base(fig, 380, True, 44)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="NIRF rank band in the earlier year"); fig.update_yaxes(title="Institution-years (count)")
    return fig, int(len(leave)), int((leave > 50).sum())


# ----------------------------------------------------------------------------------- cleaning
def before_after():
    raw = D.RAW
    cats, before, after = [], [], []
    if raw is not None:
        cats = ["NIRF ids", "Name spellings", "Locations"]
        before = [raw.nirf_id.nunique(), raw.name.nunique(), raw.location.nunique()]
        after = [D.J.id_new.nunique(), D.J.name_new.nunique(), D.J.location_clean.nunique()]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cats, y=before, name="Before cleaning", marker=dict(color=ROSE, pattern=dict(shape="x", fgcolor=INK, size=6), line=dict(color=INK, width=1.3)),
                         text=before, textposition="outside"))
    fig.add_trace(go.Bar(x=cats, y=after, name="After cleaning", marker=dict(color=TEAL, line=dict(color=INK, width=1.3)),
                         text=after, textposition="outside"))
    base(fig, 400, True, 44)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Distinct values (count)", range=[0, max(before + [1]) * 1.18])
    fig.update_xaxes(title="Field in the NIRF table")
    return fig, (before, after)


def lineage_dumbbell():
    g = D.J[D.J.year == 2025].nlargest(14, "lineage_ratio").sort_values("lineage_ratio")
    fig = go.Figure()
    for _, r in g.iterrows():
        fig.add_trace(go.Scatter(x=[r.pubs_own, r.pubs_lineage], y=[r["label"]] * 2, mode="lines", line=dict(color=INK, width=2), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=g.pubs_own, y=g["label"], mode="markers", name="Own count (used)", marker=dict(size=13, color=TEAL, line=dict(color=INK, width=1.5))))
    fig.add_trace(go.Scatter(x=g.pubs_lineage, y=g["label"], mode="markers", name="Lineage count (institution + units)", marker=dict(size=13, color=CREAM, symbol="square", line=dict(color=RUST, width=3))))
    base(fig, 460, True, 44)
    fig.update_layout(margin=dict(l=230, r=24, t=44, b=56))
    fig.update_xaxes(type="log", title="Papers in the 3-year window (log scale)", tickvals=[10,30,100,300,1000,3000,10000,30000], ticktext=["10","30","100","300","1k","3k","10k","30k"])
    return fig, int((D.J[D.J.year == 2025].lineage_ratio > 1.05).sum())


def outliers_plot():
    g = D.J
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g.pubs_own, y=g.rpc, mode="markers", name="All institution-years",
                             marker=dict(size=7, color=rgba(TAUPE, 0.55), line=dict(color=TAUPE, width=0.6)), hoverinfo="skip"))
    if D.OUT is not None and len(D.OUT):
        o = D.OUT.merge(g[["year", "id_new", "name"]], on=["year", "id_new"], how="left")
        fig.add_trace(go.Scatter(x=o.pubs_own, y=o.rpc, mode="markers", name="Flagged outliers", text=o.name_y if "name_y" in o else o.name,
                                 marker=dict(size=16, symbol="diamond-open", color=RUST, line=dict(color=RUST, width=3)),
                                 hovertemplate="%{text}<br>%{x:,.0f} papers<br>score %{y:.1f}<extra></extra>"))
    base(fig, 420, True, 44)
    fig.update_xaxes(type="log", title="Papers in the 3-year window (log scale)", tickvals=[10,30,100,300,1000,3000,10000,30000], ticktext=["10","30","100","300","1k","3k","10k","30k"]); fig.update_yaxes(title="NIRF research score (0 to 100)")
    return fig


def missing_funnel():
    L = D.LOG
    steps = [("NIRF rows scraped", len(D.RAW) if D.RAW is not None else len(D.J)), ("After cleaning and ID matching", len(D.J)),
             ("Matched to OpenAlex", int(D.J.openalex_id.notna().sum())), ("With full 3-year window", int((D.J.n_oa_years == 3).sum())),
             ("Not flagged by any check", int((~D.J.flag_any).sum()))]
    fig = go.Figure(go.Funnel(y=[s[0] for s in steps], x=[s[1] for s in steps], textinfo="value+percent initial",
                              marker=dict(color=[NAVY, TEAL, SAGE, MUSTARD, RUST], line=dict(color=INK, width=1.5)),
                              connector=dict(line=dict(color=INK, width=1))))
    base(fig, 380, False, 10)
    fig.update_layout(margin=dict(l=230, r=20, t=10, b=20))
    return fig


def gauge(value, label):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number=dict(font=dict(family=DISPLAY, size=44, color=INK), valueformat=".2f"),
                                 gauge=dict(axis=dict(range=[0, 1], tickcolor=INK, tickfont=dict(size=11)),
                                            bar=dict(color=INK, thickness=0.28), bgcolor=CREAM, borderwidth=2, bordercolor=INK,
                                            steps=[dict(range=[0, 0.4], color="#F0D9C2"), dict(range=[0.4, 0.7], color="#EBCB73"),
                                                   dict(range=[0.7, 1], color="#93A97A")])))
    base(fig, 230, False, 20)
    fig.update_layout(margin=dict(l=20, r=20, t=26, b=6))
    return fig


# ----------------------------------------------------------------------------------- charts from lectures 6 to 8
def small_multiples(metric, types):
    """lecture 7: one small chart per group, all on the same axes"""
    from plotly.subplots import make_subplots
    per, rk, gp, word, axis = metric_cols(metric)
    j = _sub(D.J, types)
    present = [t for t in TYPES if (j.type == t).any()]
    cols = 4
    nrow = int(np.ceil(len(present) / cols)) or 1
    rho_txt = {t: D.rho(j[j.type == t], "rpc", per) for t in present}
    fig = make_subplots(rows=nrow, cols=cols, shared_xaxes=True, shared_yaxes=True, horizontal_spacing=0.025, vertical_spacing=0.17,
                        subplot_titles=[f"{t} (n={int((j.type == t).sum())}, rho {rho_txt[t]:.2f})" if pd.notna(rho_txt[t]) else t for t in present])
    lo, hi = np.log10(D.J[per].min()) - .08, np.log10(D.J[per].max()) + .08
    for k, t in enumerate(present):
        g = j[j.type == t]
        fig.add_trace(go.Scatter(x=g[per], y=g.rpc, mode="markers", name=t, showlegend=False, text=g.name + " " + g.year.astype(str),
                                 marker=dict(size=7, color=TYPE_COL[t], symbol=TYPE_SYM[t], opacity=.8, line=dict(color=INK, width=.5)),
                                 hovertemplate="%{text}<br>%{x:,.0f} " + word + "/yr<br>score %{y:.1f}<extra></extra>"), row=k // cols + 1, col=k % cols + 1)
    base(fig, 250 * nrow + 90, False, 40)
    fig.update_xaxes(type="log", range=[lo, hi], tickvals=[100, 1000, 10000], ticktext=["100", "1k", "10k"])
    fig.update_yaxes(range=[0, 100])
    fig.update_annotations(font=dict(size=12.5, family=FONT, color=INK))
    fig.update_layout(margin=dict(l=62, r=14, t=40, b=70))
    fig.add_annotation(text=axis, x=0.5, y=-0.14, xref="paper", yref="paper", showarrow=False, font=dict(size=13))
    fig.add_annotation(text="NIRF research score (0 to 100)", x=-0.055, y=0.5, xref="paper", yref="paper", textangle=-90, showarrow=False, font=dict(size=13))
    return fig, rho_txt, {t: int((j.type == t).sum()) for t in present}


def histograms(year, types):
    """lecture 6: how one measure is spread"""
    from plotly.subplots import make_subplots
    g = _sub(D.J[D.J.year == year], types)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12, subplot_titles=("Research score", "Papers per year (log scale)"))
    fig.add_trace(go.Histogram(x=g.rpc, xbins=dict(start=0, end=100, size=10), marker=dict(color=NAVY, line=dict(color=CREAM, width=1.5)),
                               hovertemplate="score %{x}<br>%{y} institutions<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Histogram(x=np.log10(g.papers_per_year), xbins=dict(start=1, end=4.6, size=0.3), marker=dict(color=TEAL, line=dict(color=CREAM, width=1.5)),
                               hovertemplate="10^%{x:.1f} papers per year<br>%{y} institutions<extra></extra>"), row=1, col=2)
    base(fig, 360, False, 40)
    tx, tt = logticks(1.0, 4.6)
    fig.update_xaxes(title="NIRF research score (0 to 100)", row=1, col=1)
    fig.update_xaxes(title="Papers per year", tickvals=tx, ticktext=tt, row=1, col=2)
    fig.update_yaxes(title="Institutions (count)", rangemode="tozero")
    fig.update_annotations(font=dict(size=14, family=FONT, color=INK))
    fig.update_layout(bargap=0.04)
    return fig


def corr_heat(year, types):
    """lecture 6: a correlation matrix needs a diverging scale centred on 0"""
    g = _sub(D.J[D.J.year == year], types)
    cols = {"Teaching": "tlr", "Research": "rpc", "Graduation": "go", "Outreach": "oi", "Perception": "pr", "Papers": "pubs_own", "Citations": "cites_received"}
    r = g[list(cols.values())].rank().corr()
    r.index = r.columns = list(cols)
    z = r.values
    fig = go.Figure(go.Heatmap(z=z, x=list(cols), y=list(cols), zmin=-1, zmax=1, colorscale=DIV, xgap=2, ygap=2,
                               text=np.round(z, 2), texttemplate="%{text}", textfont=dict(size=11),
                               colorbar=dict(title="Spearman", thickness=12, len=0.8),
                               hovertemplate="%{y} and %{x}: %{z:.2f}<extra></extra>"))
    base(fig, 360, False, 10)
    fig.update_layout(margin=dict(l=90, r=20, t=10, b=70))
    fig.update_yaxes(autorange="reversed")
    return fig, r


def type_stack(types):
    """lecture 7: parts of a total, bars from zero"""
    j = _sub(D.J, types)
    t = j.groupby(["year", "type"]).size().unstack(fill_value=0).reindex(columns=TYPES, fill_value=0)
    fig = go.Figure()
    for ty in TYPES:
        if t[ty].sum() == 0:
            continue
        fig.add_trace(go.Bar(x=t.index.astype(str), y=t[ty], name=ty, marker=dict(color=TYPE_COL[ty], line=dict(color=CREAM, width=1.2)),
                             hovertemplate=ty + "<br>%{x}: %{y} institutions<extra></extra>"))
    base(fig, 380, True, 44)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="NIRF ranking year"); fig.update_yaxes(title="Institutions in the top 100 (count)")
    return fig, t
