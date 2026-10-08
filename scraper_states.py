import csv
import json
import urllib.request
from datetime import datetime, timezone

# Flux officiel FiveThirtyEight des sondages du Sénat
SENATE_POLLS_URL = "https://projects.fivethirtyeight.com/polls-page/data/senate_polls.csv"

TARGET_STATES = {
    "PA": {"name": "Pennsylvanie", "alt": ["pa", "pennsylvania"]},
    "GA": {"name": "Géorgie", "alt": ["ga", "georgia"]},
    "AZ": {"name": "Arizona", "alt": ["az", "arizona"]},
    "NV": {"name": "Nevada", "alt": ["nv", "nevada"]},
    "WI": {"name": "Wisconsin", "alt": ["wi", "wisconsin"]},
    "MI": {"name": "Michigan", "alt": ["mi", "michigan"]},
    "NC": {"name": "Caroline du Nord", "alt": ["nc", "north carolina"]},
    "TX": {"name": "Texas", "alt": ["tx", "texas"]}
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
            # Filtrer les sondages de l'État
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

                # Conserve les 5 sondages récents de chaque camp pour calculer la moyenne
                if 'dem' in party and len(dem_scores) < 5:
                    dem_scores.append(pct)
                elif 'rep' in party and len(rep_scores) < 5:
                    rep_scores.append(pct)

            if dem_scores and rep_scores:
                dem_val = round(sum(dem_scores) / len(dem_scores), 1)
                rep_val = round(sum(rep_scores) / len(rep_scores), 1)
                margin = round(dem_val - rep_val, 1)

                states_result[code] = {
                    "name": config["name"],
                    "dem": dem_val,
                    "rep": rep_val,
                    "margin": margin,
                    "leading": "DEM" if margin > 0 else "REP"
                }
                print(f"Extraction OK {config['name']} : DEM {dem_val}% / REP {rep_val}%")
            else:
                print(f"Aucun sondage récent trouvé pour {config['name']}")

    except Exception as e:
        print(f"Erreur téléchargement : {e}")

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Mise à jour terminée : {len(states_result)} États enregistrés.")

if __name__ == "__main__":
    fetch_state_polling()
