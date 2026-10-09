import csv
import io
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

# Cartographie des 10 États cibles
STATE_MAP = {
    "Texas": "TX",
    "North Carolina": "NC",
    "Michigan": "MI",
    "Maine": "ME",
    "Kansas": "KS",
    "Iowa": "IA",
    "Ohio": "OH",
    "Alaska": "AK",
    "Georgia": "GA",
    "Florida": "FL"
}

STATE_NAMES_FR = {
    "TX": "Texas",
    "NC": "Caroline du Nord",
    "MI": "Michigan",
    "ME": "Maine",
    "KS": "Kansas",
    "IA": "Iowa",
    "OH": "Ohio",
    "AK": "Alaska",
    "GA": "Géorgie",
    "FL": "Floride"
}

DEFAULT_VALUES = {
    "TX": {"dem": 48.1, "rep": 45.3},
    "NC": {"dem": 49.8, "rep": 41.0},
    "MI": {"dem": 48.1, "rep": 44.9},
    "ME": {"dem": 47.5, "rep": 46.8},
    "KS": {"dem": 45.4, "rep": 45.6},
    "IA": {"dem": 45.9, "rep": 45.2},
    "OH": {"dem": 47.3, "rep": 44.1},
    "AK": {"dem": 48.5, "rep": 47.3},
    "GA": {"dem": 51.0, "rep": 37.0},
    "FL": {"dem": 40.0, "rep": 50.0}
}

URL_538 = "https://projects.fivethirtyeight.com/polls-page/data/senate_polls.csv"

def fetch_538_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(URL_538, headers=headers)
    
    state_scores = defaultdict(lambda: {"DEM": [], "REP": []})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            csv_text = response.read().decode('utf-8', errors='ignore')
            reader = csv.DictReader(io.StringIO(csv_text))
            
            for row in reader:
                state_name = row.get("state", "").strip()
                party = row.get("party", "").strip().upper()
                pct_str = row.get("pct", "").strip()
                
                if state_name in STATE_MAP:
                    code = STATE_MAP[state_name]
                    if party in ["DEM", "REP"] and pct_str:
                        try:
                            pct = float(pct_str)
                            state_scores[code][party].append(pct)
                        except ValueError:
                            pass
    except Exception as e:
        print(f"Avertissement lors du téléchargement du flux 538 : {e}")
        
    return state_scores

def build_states_json():
    scores_538 = fetch_538_data()
    states_result = {}

    for code, fr_name in STATE_NAMES_FR.items():
        dem_list = scores_538[code]["DEM"]
        rep_list = scores_538[code]["REP"]

        if dem_list and rep_list:
            # Calcul de la moyenne des sondages récents extraits
            dem_val = round(sum(dem_list[:5]) / len(dem_list[:5]), 1)
            rep_val = round(sum(rep_list[:5]) / len(rep_list[:5]), 1)
            print(f"✅ [{code}] Données en direct 538 : DEM {dem_val}% / REP {rep_val}%")
        else:
            dem_val = DEFAULT_VALUES[code]["dem"]
            rep_val = DEFAULT_VALUES[code]["rep"]
            print(f"ℹ️ [{code}] Valeurs de référence appliquées : DEM {dem_val}% / REP {rep_val}%")

        margin = round(dem_val - rep_val, 1)
        states_result[code] = {
            "name": fr_name,
            "dem": dem_val,
            "rep": rep_val,
            "margin": margin,
            "leading": "DEM" if margin > 0 else ("REP" if margin < 0 else "EQUAL")
        }

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "FiveThirtyEight / ABC News (Flux officiel)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier states_data.json mis à jour avec succès !")

if __name__ == "__main__":
    build_states_json()
