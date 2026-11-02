# Does the NIRF Overall research score track independent publication and citation counts?

DA2402 Data Curation and Visualization, project 15. NIRF Overall 2017 to 2025 against OpenAlex papers and citations.

Team: Bhanu Manideep (DA25B024), Sasanka Mouli (DA25B013), Kushal V (DA25B019).

## Where things go

This README, `requirements.txt`, `.gitignore`, `.env.example` and `notebooks/` are added to the project folder you already have. Nothing else is replaced.

```
README.md                 (this file; the notebooks look for it to find the project folder)
requirements.txt
.env                      your OpenAlex key, never shared
ror_manual.csv            hand decisions for ROR matches
raw/                      untouched downloads (NIRF pages, robots.txt, OpenAlex JSON cache)
interim/                  parsed tables, crosswalks, tests and logs
clean/                    final tables and data_dictionary.csv
data/                     SQLite database
notebooks/                collection and cleaning code, run in order
retro5/                   the dashboard (python app.py)
*.py                      the original scripts, kept as they were
```

## Notebooks, in order

| # | Notebook | Needs internet | Original script |
|---|----------|----------------|-----------------|
| 1 | 01_collect_nirf | yes | NIRF Overall Scrape.py |
| 2 | 02_build_clean_nirf | no | Build Clean Script - IITM DA2402.py |
| 3 | 03_match_ror | yes | IITM DA2402 ROR Match.py |
| 4 | 04_collect_openalex | yes, key in .env | OpenAlex Collect IITM Project.py |
| 5 | 05_profile_raw_files | no | new: shape, dtypes, empty cells and meaning of every column |
| 6 | 06_join_analyse | no | Join Analyse IITM DA2402.py |
| 7 | 07_clean_check_and_store | no | Clean Store 06.py and Dictionary Ranges 07.py |

The code in each notebook is the script's code, unchanged. Only the path to `.env` (now the project folder) is different.

Notebooks 2 and 5 to 7 were run on a copy of the project data and keep their outputs. Notebooks 1, 3 and 4 call websites and are saved unrun.

Important: every step reads the newest dated file in its folder. A trial run of step 4 (`--limit 3`) writes a new, tiny crosswalk that becomes the newest and breaks step 6. If you do a trial, delete the files it wrote.

## Dashboard

```
pip install -r requirements.txt
cd retro5
python app.py
```
