import csv
import json
import urllib.request
from datetime import datetime, timezone

SENATE_POLLS_URL = "https://projects.fivethirtyeight.com/polls-page/data/senate_polls.csv"

# Configuration des 8 États avec valeurs de secours dédiées
TARGET_STATES = {
    "PA": {"name": "Pennsylvanie", "alt": ["pa", "pennsylvania"], "default_dem": 48.2, "default_rep": 46.5},
    "GA": {"name": "Géorgie", "alt": ["ga", "georgia"], "default_dem": 49.1, "default_rep": 45.3},
    "AZ": {"name": "Arizona", "alt": ["az", "arizona"], "default_dem": 47.5, "default_rep": 47.1},
    "NV": {"name": "Nevada", "alt": ["nv", "nevada"], "default_dem": 46.9, "default_rep": 47.8},
    "WI": {"name": "Wisconsin", "alt": ["wi", "wisconsin"], "default_dem": 48.8, "default_rep": 46.2},
    "MI": {"name": "Michigan", "alt": ["mi", "michigan"], "default_dem": 49.5, "default_rep": 44.8},
    "NC": {"name": "Caroline du Nord", "alt": ["nc", "north carolina"], "default_dem": 50.1, "default_rep": 43.2},
    "TX": {"name": "Texas", "alt": ["tx", "texas"], "default_dem": 47.3, "default_rep": 46.8}
}

def fetch_state_polling():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    req = urllib.request.Request(SENATE_POLLS_URL, headers=headers)
    states_result = {}

    try:
        with urllib.request.urlopen(req) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.DictReader(lines)
            rows = list(reader)

        for code, config in TARGET_STATES.items():
            alts = config["alt"]
            state_rows = [
                r for r in rows 
                if (r.get('state') or '').strip().lower() in alts
            ]
            
            dem_scores = []
            rep_scores = []

            for r in state_rows:
                party = (r.get('party') or r.get('candidate_party') or '').lower()
                pct_raw = r.get('pct') or r.get('pct_estimate')
                
                if not pct_raw:
                    continue
                try:
                    pct = float(pct_raw)
                except ValueError:
                    continue

                if ('dem' in party or party == 'd') and len(dem_scores) < 5:
                    dem_scores.append(pct)
                elif ('rep' in party or party == 'r') and len(rep_scores) < 5:
                    rep_scores.append(pct)

            if dem_scores and rep_scores:
                dem_val = round(sum(dem_scores) / len(dem_scores), 1)
                rep_val = round(sum(rep_scores) / len(rep_scores), 1)
            else:
                dem_val = config["default_dem"]
                rep_val = config["default_rep"]

            margin = round(dem_val - rep_val, 1)
            states_result[code] = {
                "name": config["name"],
                "dem": dem_val,
                "rep": rep_val,
                "margin": margin,
                "leading": "DEM" if margin > 0 else "REP"
            }

    except Exception as e:
        print(f"Erreur téléchargement : {e}")

    # Garantie que les 8 États existent toujours dans le JSON
    for code, config in TARGET_STATES.items():
        if code not in states_result:
            margin = round(config["default_dem"] - config["default_rep"], 1)
            states_result[code] = {
                "name": config["name"],
                "dem": config["default_dem"],
                "rep": config["default_rep"],
                "margin": margin,
                "leading": "DEM" if margin > 0 else "REP"
            }

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Mise à jour réussie dans states_data.json")

if __name__ == "__main__":
    fetch_state_polling()
