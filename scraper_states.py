import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-paxton",
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-cornyn"
        ],
        "default_dem": 48.1, "default_rep": 45.3
    },
    "NC": {
        "name": "Caroline du Nord",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/cooper-vs-whatley",
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/whatley-vs-cooper"
        ],
        "default_dem": 49.8, "default_rep": 41.0
    },
    "MI": {
        "name": "Michigan",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-el-sayed",
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-stevens"
        ],
        "default_dem": 48.1, "default_rep": 44.9
    },
    "ME": {
        "name": "Maine",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-platner",
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-jackson"
        ],
        "default_dem": 47.5, "default_rep": 46.8
    },
    "KS": {
        "name": "Kansas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/marshall-vs-hamilton",
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/hamilton-vs-marshall"
        ],
        "default_dem": 45.4, "default_rep": 45.6
    },
    "IA": {
        "name": "Iowa",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/turek-vs-hinson",
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/hinson-vs-turek"
        ],
        "default_dem": 45.9, "default_rep": 45.2
    },
    "OH": {
        "name": "Ohio",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/ohio/brown-vs-husted",
            "https://www.realclearpolling.com/polls/senate/general/2026/ohio/husted-vs-brown"
        ],
        "default_dem": 47.3, "default_rep": 44.1
    },
    "AK": {
        "name": "Alaska",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/alaska/peltola-vs-sullivan",
            "https://www.realclearpolling.com/polls/senate/general/2026/alaska/sullivan-vs-peltola"
        ],
        "default_dem": 48.5, "default_rep": 47.3
    },
    "GA": {
        "name": "Géorgie",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/ossoff-vs-taylor-greene",
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/taylor-greene-vs-ossoff"
        ],
        "default_dem": 51.0, "default_rep": 37.0
    },
    "FL": {
        "name": "Floride",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/florida/nixon-vs-moody",
            "https://www.realclearpolling.com/polls/senate/general/2026/florida/moody-vs-nixon"
        ],
        "default_dem": 40.0, "default_rep": 50.0
    }
}

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.realclearpolling.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def extract_rcp_data(html_content):
    # Suppression des balises HTML pour obtenir le texte brut
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = re.sub(r'\s+', ' ', clean_text)

    # 1. Détection de l'ordre des partis (Democrat vs Republican)
    d_pos = re.search(r'\([D|Democrat]\)', clean_text, re.I)
    r_pos = re.search(r'\([R|Republican|GOP]\)', clean_text, re.I)

    dem_first = True
    if d_pos and r_pos:
        dem_first = (d_pos.start() < r_pos.start())

    # 2. Extraction du bloc "RCP Average"
    idx = clean_text.lower().find("rcp average")
    if idx != -1:
        snippet = clean_text[idx:idx+300]
        
        # Nettoyage des plages de dates (ex: 9/15 - 10/6)
        snippet = re.sub(r'\d{1,2}/\d{1,2}(?:\s*-\s*\d{1,2}/\d{1,2})?', ' ', snippet)
        snippet = re.sub(r'[—\-\|,]', ' ', snippet)

        # Isolement des pourcentages valides entre 20% et 80%
        nums = [float(x) for x in re.findall(r'\b(\d{2}(?:\.\d)?)\b', snippet) if 20.0 <= float(x) <= 80.0]

        if len(nums) >= 2:
            dem_score = nums[0] if dem_first else nums[1]
            rep_score = nums[1] if dem_first else nums[0]
            return dem_score, rep_score

    return None, None

def fetch_live_data():
    session = requests.Session()
    states_result = {}

    for code, config in TARGET_RACES.items():
        dem_val, rep_val = None, None

        for url in config["urls"]:
            try:
                resp = session.get(url, headers=HEADERS, impersonate="chrome120", timeout=12)
                if resp.status_code == 200:
                    d, r = extract_rcp_data(resp.text)
                    if d is not None and r is not None:
                        dem_val, rep_val = d, r
                        print(f"✅ [{code}] Extrait en direct RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception as e:
                print(f"⚠️ [{code}] Erreur d'accès à {url} : {e}")

        if dem_val is None or rep_val is None:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
            print(f"ℹ️ [{code}] Données de secours appliquées : DEM {dem_val}% / REP {rep_val}%")

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
        "source": "RealClearPolling (En direct)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Extraction terminée et enregistrée dans states_data.json")

if __name__ == "__main__":
    fetch_live_data()
