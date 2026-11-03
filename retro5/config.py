TITLE = "PaperRank"
SUBTITLE = "Does the NIRF Overall research score track OpenAlex papers and citations? 164 institutions, 2017 to 2025"
COURSE = "DA2402 Data Curation and Visualisation, IIT Madras"
REF = "DA2402/15"

TEAM = [
    ("Bhanu Manideep", "DA25B024", "ROR and OpenAlex scraping, data cleaning"),
    ("Sasanka Mouli", "DA25B013", "NIRF scraping, data cleaning"),
    ("Kushal V", "DA25B019", "Visualisation and dashboard"),
]

SOURCES = [
    ("NIRF Overall ranking pages, one per year 2017 to 2025: https://www.nirfindia.org/Rankings/<year>/OverallRanking.html",
     "Rank and the five component scores for each institution and year",
     "No robots.txt is published: https://www.nirfindia.org/robots.txt returns 404 in a browser (checked 2026-11-03; a plain curl request returned 403). No terms-of-use or licence page was found on the site. The only notice is the footer: “Copyright © 2023 Website Managed and Maintained by INFLIBNET CENTRE”. The data was collected for non-commercial academic research and is not redistributed. No licence is assumed beyond fair dealing for research (Copyright Act, 1957, s. 52(1)(a)).",
     "2026-11-03"),
    ("OpenAlex API: https://api.openalex.org (institutions and works, grouped by publication year)",
     "Papers and citations per institution and year; institution records",
     "OpenAlex data is released under CC0 (public domain).",
     "2026-11-01"),
    ("ROR API v2: https://api.ror.org/v2/organizations",
     "Research Organization Registry ids used to match NIRF names to OpenAlex",
     "ROR data is released under CC0 1.0.",
     "2026-11-01"),
]

LIBRARIES = [
    ("Python 3", "PSF licence"), ("pandas, numpy", "BSD-3-Clause"), ("requests", "Apache-2.0"),
    ("Beautiful Soup 4", "MIT"), ("Plotly and Dash", "MIT"), ("SQLite (standard library)", "public domain"),
    ("Libre Franklin and Source Serif 4 fonts (Google Fonts)", "SIL Open Font Licence 1.1"),
]

AI_TOOLS = [
    ("Claude (Anthropic)", "Drafted and reviewed scripts for scraping, cleaning, matching, collection, analysis and "
     "this dashboard; helped plan the design. The team ran every script, checked the outputs and made the decisions."),
]
