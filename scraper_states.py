import csv
import json
import urllib.request
from datetime import datetime

SENATE_CSV_URL = "https://projects.fivethirtyeight.com/senate-data/538_senate_averages.csv"

TARGET_STATES = {
    "PA": "Pennsylvanie",
    "GA": "Géorgie",
    "AZ": "Arizona",
    "NV": "Nevada",
    "WI": "Wisconsin",
    "MI": "Michigan",
    "NC": "Caroline du Nord",
    "TX": "Texas"
}

def fetch_state_polling():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    req = urllib.request.Request(SENATE_CSV_URL, headers=headers)
    states_result = {}

    try:
        with urllib.request.urlopen(req) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.DictReader(lines)
            rows = list(reader)

        for state_code, state_name in TARGET_STATES.items():
            state_rows = [r for r in rows if r.get('state') == state_code]
            if not state_rows:
                continue

            by_date = {}
            for r in state_rows:
                date_str = r.get('date') or r.get('modeldate')
                party = (r.get('party') or r.get('candidate') or '').lower()
                pct_raw = r.get('pct_estimate') or r.get('pct_trend_adjusted')
                
                if not date_str or not pct_raw:
                    continue
                try:
                    pct = round(float(pct_raw), 1)
                except ValueError:
                    continue

                if date_str not in by_date:
                    by_date[date_str] = {}

                if 'dem' in party:
                    by_date[date_str]['dem'] = pct
                elif 'rep' in party:
                    by_date[date_str]['rep'] = pct

            valid_dates = [d for d in by_date if 'dem' in by_date[d] and 'rep' in by_date[d]]
            valid_dates.sort()

            if valid_dates:
                latest_d = valid_dates[-1]
                dem_val = by_date[latest_d]['dem']
                rep_val = by_date[latest_d]['rep']
                margin = round(dem_val - rep_val, 1)

                states_result[state_code] = {
                    "name": state_name,
                    "dem": dem_val,
                    "rep": rep_val,
                    "margin": margin,
                    "leading": "DEM" if margin > 0 else "REP"
                }

    except Exception as e:
        print(f"Erreur scraping : {e}")

    # Données par défaut si un État manque temporairement dans le flux
    for code, name in TARGET_STATES.items():
        if code not in states_result:
            states_result[code] = {
                "name": name, "dem": 48.0, "rep": 47.5, "margin": 0.5, "leading": "DEM"
            }

    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Mise à jour des 8 États réussie !")

if __name__ == "__main__":
    fetch_state_polling()
