"""
Revaluation of NIRF research marks - Dash app.

Run from this folder:   python app.py      then open http://127.0.0.1:8050
Open http://127.0.0.1:8050/?mode=sarkari to start in the government-portal look.
"""
import random
import dash
from dash import Dash, html, dcc, Input, Output, State, ctx, no_update
import data as D
import pages as P
import config as K

app = Dash(__name__, suppress_callback_exceptions=True, title=K.TITLE, update_title=None)
server = app.server

TABS = [("result", "Result"), ("q1", "Q1 Does it track?"), ("q2", "Q2 Who was re-marked?"), ("sheet", "Marksheet"),
        ("viva", "Viva"), ("q3", "Q3 Can we trust it?"), ("method", "Method")]
SUBS = {
    "q1": [("years", "Over the years"), ("year", "One year up close"), ("split", "Top half vs bottom half")],
    "q2": [("gaps", "Biggest revisions"), ("slope", "Slope chart"), ("types", "By type")],
    "q3": [("robust", "Robustness"), ("limits", "Limitations")],
    "method": [("collect", "Collection"), ("clean", "Cleaning"), ("store", "Storage"), ("credits", "Credits")],
}
NEEDS_YEAR = {"q1", "q2", "sheet"}
NEEDS_METRIC = {"q1", "q2", "sheet"}


def radio(id_, options, value, cls):
    return dcc.RadioItems(id=id_, options=[{"label": l, "value": v} for v, l in options], value=value, className=cls,
                          inline=True, inputClassName="r-in", labelClassName="r-lab")


def slot(n, label):
    return html.Div(className=f"slot slot{n}", children=html.Span(label))


gov_chrome = html.Div(className="gov-only gov-chrome", children=[
    html.Div(className="tricolour"),
    html.Div(className="gov-util", children=[html.Span(t) for t in
             ["Skip to main content", "|", "Screen reader access", "|", "A-  A  A+", "|", "हिन्दी", "|", "English"]]),
    html.Div(className="gov-banner", children=[
        html.Div("logo slot (add yours)", className="slot slot-logo"),
        html.Div(className="gov-title", children=[
            html.Div("Directorate of Revaluation of Research Marks"),
            html.Small("(An Autonomous Body under the Ministry of Marks and Re-marks)")]),
        slot(1, "photo slot 1: Hon'ble"),
    ]),
    html.Div(className="gov-nav", children=[html.Span(t) for t in
             ["Home", "About Us ▾", "Schemes ▾", "Circulars", "RTI", "Citizen's Charter", "Tenders", "Contact Us"]]),
    html.Div(className="gov-carousel", children=[slot(2, "photo slot 2"), slot(3, "photo slot 3"), slot(4, "photo slot 4"),
                                                 html.Div("carousel 1 of 12", className="gov-count")]),
    html.Div(className="gov-ticker", children=html.Span(
        "Latest: Last date to submit grievances extended to 31/12/2026   ●   Click here for tender notice (PDF, 24 MB) NEW   "
        "●   Server will be down for maintenance   ●   Applicants are advised not to press Back or Refresh   ●   ")),
])

header = html.Div(className="head", children=[
    html.Div(className="head-l", children=[html.H1(K.TITLE), html.P(K.SUBTITLE)]),
    html.Button(id="theme-toggle", n_clicks=0, className="toggle", title="Switch look", children=[
        html.Span(className="sw", children=html.Span(className="knob")), html.Span("Sarkari mode", className="toggle-lab")]),
])

controls = html.Div(id="controls", className="controls", children=[
    html.Div(className="ctl", children=[html.Div("NIRF ranking year: fill one bubble", className="ctl-lab"),
                                        radio("year", [(y, str(y)) for y in D.YEARS], D.YEARS[-1], "omr")]),
    html.Div(className="ctl", children=[html.Div("Measure", className="ctl-lab"),
                                        radio("metric", [("papers", "Papers"), ("citations", "Citations")], "papers", "omr wide")]),
])

inst_controls = html.Div(id="inst-controls", className="inst hidden", children=[
    html.Div(className="inst-one", children=[html.Label("Institution"),
             dcc.Dropdown(id="inst-a", options=D.INSTITUTIONS, value=D.J[D.J.year == D.YEARS[-1]].sort_values("rank").id_new.iloc[0],
                          clearable=False, className="dd")]),
    html.Div(className="inst-one", children=[html.Label("Compare with (optional)"),
             dcc.Dropdown(id="inst-b", options=D.INSTITUTIONS, value=None, clearable=True, placeholder="None", className="dd")]),
])

footer = html.Div(className="foot", children=[
    html.Span("Sources: NIRF Overall rankings, OpenAlex, ROR. OpenAlex counts are a second opinion, not ground truth."),
    html.Span(className="gov-only", children="You are visitor no. 000901   |   Last updated: 14/03/2016   |   Best viewed in Internet Explorer 6 at 800x600"),
])

loading = html.Div(id="gov-loading", children=html.Div(className="box", children=[
    html.Div("Please wait... your request is being processed", className="l1"),
    html.Div(className="bar", children=html.Div(className="fill")),
    html.Div("99%", className="pct"),
    html.Div("Do not press Back or Refresh. You are number 4,812 in the queue.", className="l2"),
    html.A("Skip (admin only)", id="gov-skip", className="skip"),
]))

session = html.Div(id="gov-session", children=html.Div(className="box", children=[
    html.Div("Your session will expire in 00:59", className="l1"), html.Button("Extend session", id="gov-extend")]))

app.layout = html.Div(id="shell", children=[
    dcc.Location(id="url"), dcc.Store(id="theme", data=None),
    dcc.Store(id="viva-store", data={"q": None, "answered": False, "right": 0, "total": 0}),
    html.Div(id="clientside-dummy", style={"display": "none"}),
    loading, session, gov_chrome,
    html.Div(className="frame", children=[
        header, controls,
        html.Div(className="nav", children=[dcc.RadioItems(id="tab", options=[{"label": l, "value": v} for v, l in TABS], value="result",
                                                            className="tabs", inline=True, inputClassName="r-in", labelClassName="r-lab")]),
        html.Div(id="subnav", className="subnav hidden", children=dcc.RadioItems(id="sub", options=[], value=None, className="subs", inline=True,
                                                                           inputClassName="r-in", labelClassName="r-lab")),
        inst_controls,
        html.Div(id="page", className="page"),
        footer,
    ]),
])


# ------------------------------------------------------------------ callbacks
@app.callback(Output("theme", "data"), Input("url", "search"), Input("theme-toggle", "n_clicks"), State("theme", "data"))
def set_theme(search, n, current):
    if ctx.triggered_id == "theme-toggle":
        return "sarkari" if current != "sarkari" else "revaluation"
    return "sarkari" if search and "mode=sarkari" in search else "revaluation"


app.clientside_callback(
    "function(theme){ return window.dash_clientside.rev.applyTheme(theme); }",
    Output("clientside-dummy", "children"), Input("theme", "data"))


@app.callback(Output("sub", "options"), Output("sub", "value"), Output("subnav", "className"), Input("tab", "value"))
def sub_options(tab):
    subs = SUBS.get(tab)
    if not subs:
        return [], None, "subnav hidden"
    return [{"label": l, "value": v} for v, l in subs], subs[0][0], "subnav"


@app.callback(Output("controls", "className"), Output("inst-controls", "className"), Input("tab", "value"))
def show_controls(tab):
    return "controls" + ("" if tab in NEEDS_YEAR else " hidden"), ("inst" if tab == "sheet" else "inst hidden")


@app.callback(Output("page", "children"), Input("tab", "value"), Input("sub", "value"), Input("year", "value"),
              Input("metric", "value"), Input("theme", "data"), Input("inst-a", "value"), Input("inst-b", "value"))
def render(tab, sub, year, metric, theme, ia, ib):
    theme = theme or "revaluation"
    valid = [v for v, _ in SUBS.get(tab, [])]
    if valid and sub not in valid:
        sub = valid[0]
    if tab == "result":
        return P.home()
    if tab == "q1":
        return P.q1(sub, year, metric, theme)
    if tab == "q2":
        return P.q2(sub, year, metric, theme)
    if tab == "sheet":
        return P.marksheet(year, metric, theme, [ia, ib])
    if tab == "viva":
        return P.viva()
    if tab == "q3":
        return P.q3(sub, theme)
    return P.method(sub, theme)


@app.callback(Output("tab", "value"), Input("go-q1", "n_clicks"), Input("go-q2", "n_clicks"), Input("go-viva", "n_clicks"),
              prevent_initial_call=True)
def jump(a, b, c):
    t = ctx.triggered_id
    val = {"go-q1": a, "go-q2": b, "go-viva": c}.get(t)
    if not val:
        return no_update
    return {"go-q1": "q1", "go-q2": "q2", "go-viva": "viva"}[t]


@app.callback(
    Output("viva-question", "children"), Output("viva-a", "children"), Output("viva-b", "children"),
    Output("viva-result", "children"), Output("viva-score", "children"), Output("viva-store", "data"),
    Input("viva-a", "n_clicks"), Input("viva-b", "n_clicks"), Input("viva-next", "n_clicks"),
    State("viva-store", "data"))
def viva_cb(na, nb, nn, st):
    trig = ctx.triggered_id
    pool = D.VIVA_POOL
    st = dict(st)
    def score_text():
        return f"Viva score: {st['right']} right out of {st['total']}."
    answering = trig in ("viva-a", "viva-b") and ((trig == "viva-a" and na) or (trig == "viva-b" and nb))
    if answering and st.get("q") is not None and not st["answered"]:
        q = pool[st["q"]]
        flip = st["flip"]
        left, right = (q["b"], q["a"]) if flip else (q["a"], q["b"])
        winner_is_b = True
        picked_right = trig == "viva-b"
        picked = right if picked_right else left
        correct = picked == q["b"]
        st["answered"] = True
        st["total"] += 1
        st["right"] += int(correct)
        ratio = q["a_papers"] / max(q["b_papers"], 1)
        res = [html.B("Correct. " if correct else "Not quite. "),
               f"{q['b']} scored {q['b_rpc']:.1f} on research; {q['a']} scored {q['a_rpc']:.1f}, with {ratio:.1f} times the papers."]
        lq = _question(q, flip)
        return lq, no_update, no_update, res, score_text(), st
    # new question
    idx = random.randrange(len(pool))
    flip = random.random() < 0.5
    q = pool[idx]
    st.update(q=idx, answered=False, flip=flip)
    left, right = (q["b"], q["a"]) if flip else (q["a"], q["b"])
    return _question(q, flip), f"A: {left}", f"B: {right}", "", score_text(), st


def _question(q, flip):
    left, right = (q["b"], q["a"]) if flip else (q["a"], q["b"])
    lp = q["b_papers"] if flip else q["a_papers"]
    rp = q["a_papers"] if flip else q["b_papers"]
    return html.Div([
        html.Div(f"NIRF {q['year']}", className="viva-year"),
        html.Div(className="viva-pair", children=[
            html.Div([html.B("A  " + left), html.Br(), f"{lp:,} papers in the 3 years before"]),
            html.Div([html.B("B  " + right), html.Br(), f"{rp:,} papers in the 3 years before"])]),
        html.Div("Which got the higher NIRF research score?", className="viva-ask")])


if __name__ == "__main__":
    app.run(debug=False, port=8050)
