# Revaluation dashboard (DA2402 / project 15)

## Setup
1. Put this `dashboard/` folder inside the project folder, next to `clean/` and `interim/`
   (it looks for `clean/nirf_openalex_joined_*.csv`). Or set env var `DCV_ROOT` to the project folder.
2. `pip install -r requirements.txt`
3. `python app.py` then open http://127.0.0.1:8050
   - `http://127.0.0.1:8050/?mode=sarkari` starts in Sarkari mode. The button top right toggles.

## What to edit
- `config.py`: title, team names and contributions (TODO), NIRF terms-of-use quote (TODO), libraries, AI tools.
- `institution_types.csv`: created on first run from keyword rules. Check the labels by eye and fix any wrong ones; your edits are kept.
- `assets/photos/`: drop `logo.png`, `slot1.jpg`, `slot2.jpg` ... `slot4.jpg` (see README.txt there). Do not use the State Emblem.
- `assets/base.css` = Revaluation look, `assets/sarkari.css` = government mode, `assets/theme.js` = loading screen and session popup.
- `charts.py` figures, `pages.py` page text and layout, `data.py` data loading and statistics.

## Notes
- Fonts come from Google Fonts; offline, fallback serif/sans fonts are used.
- Works without the optional interim files; some tabs just show less.
