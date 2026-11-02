"""
config.py - the words you are most likely to edit: team, contributions, attributions.
Everything here is plain text. Fill in the TODO lines before you submit.
"""
TITLE = "Revaluation of NIRF research marks"
SUBTITLE = "Does the NIRF Overall research score track OpenAlex papers and citations? 164 institutions, 2017 to 2025"
COURSE = "DA2402 Data Curation and Visualisation, IIT Madras"
REF = "DA2402/15"

# name, roll number, what they did   (TODO: replace with the real team and contributions)
TEAM = [
    ("Member 1", "DA25B___", "TODO: e.g. NIRF scraping and cleaning (steps 1 and 2)"),
    ("Member 2", "DA25B___", "TODO: e.g. ROR matching and OpenAlex collection (steps 3 and 4)"),
    ("Member 3", "DA25B___", "TODO: e.g. analysis, cleaning tests and storage (steps 5 and 6)"),
    ("Member 4", "DA25B___", "TODO: e.g. dashboard and presentation"),
]

# source, what we took, licence or terms, date retrieved
SOURCES = [
    ("NIRF Overall ranking pages, 2017 to 2025 (nirfindia.org)",
     "Rank and the five component scores for each institution and year",
     "Public government web pages. TODO: quote the site's terms of use here before submission.",
     "2026-10-31"),
    ("OpenAlex API (api.openalex.org)",
     "Papers and citations per institution and year; institution records",
     "OpenAlex data is released under CC0 (public domain).",
     "2026-11-01"),
    ("ROR API (api.ror.org), v2",
     "Research Organization Registry ids used to match NIRF names to OpenAlex",
     "ROR data is released under CC0 1.0.",
     "2026-11-01"),
]

LIBRARIES = [
    ("Python 3", "PSF licence"), ("pandas, numpy", "BSD-3-Clause"), ("requests", "Apache-2.0"),
    ("Beautiful Soup 4", "MIT"), ("Plotly and Dash", "MIT"), ("SQLite (standard library)", "public domain"),
    ("Anek Latin, Martel, Kalam fonts (Google Fonts)", "SIL Open Font Licence 1.1"),
]

AI_TOOLS = [
    ("Claude (Anthropic)", "Drafted and reviewed scripts for scraping, cleaning, matching, collection, analysis and "
     "this dashboard; helped plan the design. The team ran every script, checked the outputs and made the decisions."),
]
