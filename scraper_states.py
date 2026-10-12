import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TARGET_RACES = {
    "TX": {"name": "Texas", "wiki_page": "2026_United_States_Senate_election_in_Texas", "dem_kw": "Talarico", "rep_kw": "Paxton", "default_dem": 48.1, "default_rep": 45.3},
    "NC": {"name": "Caroline du Nord", "wiki_page": "2026_United_States_Senate_election_in_North_Carolina", "dem_kw": "Cooper", "rep_kw": "Whatley", "default_dem": 49.8, "default_rep": 41.0},
    "MI": {"name": "Michigan", "wiki_page": "2026_United_States_Senate_election_in_Michigan", "dem_kw": "El-Sayed", "rep_kw": "Rogers", "default_dem": 48.1, "default_rep": 44.9},
    "ME": {"name": "Maine", "wiki_page": "2026_United_States_Senate_election_in_Maine", "dem_kw": "Jackson", "rep_kw": "Collins", "default_dem": 47.5, "default_rep": 46.8},
    "KS": {"name": "Kansas", "wiki_page": "2026_United_States_Senate_election_in_Kansas", "dem_kw": "Hamilton", "rep_kw": "Marshall", "default_dem": 45.4, "default_rep": 45.6},
    "IA": {"name": "Iowa", "wiki_page": "2026_United_States_Senate_election_in_Iowa", "dem_kw": "Turek", "rep_kw": "Hinson", "default_dem": 45.9, "default_rep": 45.2},
    "OH": {"name": "Ohio", "wiki_page": "2026_United_States_Senate_election_in_Ohio", "dem_kw": "Brown", "rep_kw": "Husted", "default_dem": 47.3, "default_rep": 44.1},
    "AK": {"name": "Alaska", "wiki_page": "2026_United_States_Senate_election_in_Alaska", "dem_kw": "Peltola", "rep_kw": "Sullivan", "default_dem": 48.5, "default_rep": 47.3},
    "GA": {"name": "Géorgie", "wiki_page": "2026_United_States_Senate_election_in_Georgia", "dem_kw": "Ossoff", "rep_kw": "Greene", "default_dem": 51.0, "default_rep": 37.0},
    "FL": {"name": "Floride", "wiki_page": "2026_United_States_Senate_election_in_Florida", "dem_kw": "Nixon", "rep_kw": "Moody", "default_dem": 40.0, "default_rep": 47.0}
}

HEADERS = {'User-Agent': 'MidtermsWidget/1.0 (https://github.com/fabparis26/midterms-widget)'}

def fetch_wiki_html(page_title):
    api_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page_title)}&format=json&prop=text"
    req = urllib.request.Request(api_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if 'parse' in data and 'text' in data['parse']:
                return data['parse']['text']['*']
    except Exception as e:
        print(f"  Erreur API Wikipedia ({page_title}) : {e}")
    return ""

def fetch_live_data():
    states_result = {}
    print("Connexion à l'API Wikipedia...")
    
    main_html = fetch_wiki_html("2026_United_States_Senate_elections")
    main_clean = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', main_html))

    for code, config in TARGET_RACES.items():
        state_html = fetch_wiki_html(config["wiki_page"])
        combined_text = main_clean + " " + re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', state_html))

        dem_kw = config["dem_kw"]
        rep_kw = config["rep_kw"]

        dem_matches = re.findall(rf'{dem_kw}[^0-9]{{0,30}}(\d{{2}}(?:\.\d)?)|(\d{{2}}(?:\.\d)?)[^0-9]{{0,30}}{dem_kw}', combined_text, re.IGNORECASE)
        rep_matches = re.findall(rf'{rep_kw}[^0-9]{{0,30}}(\d{{2}}(?:\.\d)?)|(\d{{2}}(?:\.\d)?)[^0-9]{{0,30}}{rep_kw}', combined_text, re.IGNORECASE)

        dem_val, rep_val = None, None

        for m in dem_matches:
            val = float(m[0] or m[1])
            if 35.0 <= val <= 65.0:
                dem_val = val
                break

        for m in rep_matches:
            val = float(m[0] or m[1])
            if 35.0 <= val <= 65.0:
                rep_val = val
                break

        if dem_val is not None and rep_val is not None:
            print(f"[{code}] Données en direct Wikipedia : DEM {dem_val}% / REP {rep_val}%")
        else:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
            print(f"[{code}] Sécurité activée : DEM {dem_val}% / REP {rep_val}%")

        margin = round(dem_val - rep_val, 1)
        states_result[code] = {
            "name": config["name"],
            "dem": dem_val,
            "rep": rep_val,
            "margin": margin,
            "leading": "DEM" if margin > 0 else ("REP" if margin < 0 else "EQUAL")
        }

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Wikipedia API (En direct)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Fichier states_data.json généré avec succès !")

if __name__ == "__main__":
    fetch_live_data()
