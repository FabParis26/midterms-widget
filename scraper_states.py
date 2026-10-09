import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-paxton",
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/paxton-vs-talarico"
        ],
        "default_dem": 48.4, "default_rep": 45.3
    },
    "IA": {
        "name": "Iowa",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/turek-vs-hinson",
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/hinson-vs-turek"
        ],
        "default_dem": 46.2, "default_rep": 45.2
    },
    "ME": {
        "name": "Maine",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/jackson-vs-collins",
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-jackson"
        ],
        "default_dem": 48.1, "default_rep": 47.4
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
    "KS": {
        "name": "Kansas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/hamilton-vs-marshall",
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/marshall-vs-hamilton"
        ],
        "default_dem": 48.0, "default_rep": 45.0
    },
    "MI": {
        "name": "Michigan",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/el-sayed-vs-rogers",
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-el-sayed"
        ],
        "default_dem": 48.1, "default_rep": 44.9
    },
    "NC": {
        "name": "Caroline du Nord",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/cooper-vs-whatley",
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/whatley-vs-cooper"
        ],
        "default_dem": 50.0, "default_rep": 43.0
    },
    "GA": {
        "name": "Géorgie",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/ossoff-vs-taylor-greene",
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/senate"
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
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def parse_rcp_html(html):
    # 1. Extraction dans les scripts JS embarqués (données brutes)
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in scripts:
        if 'party' in s and ('value' in s or 'score' in s):
            dem_m = re.findall(r'"party"\s*:\s*"(?:DEM|D)"[^}]*?"(?:value|score|pct)"\s*:\s*"?(\d{1,2}\.\d|\d{1,2})"?', s, re.IGNORECASE)
            rep_m = re.findall(r'"party"\s*:\s*"(?:REP|R|GOP)"[^}]*?"(?:value|score|pct)"\s*:\s*"?(\d{1,2}\.\d|\d{1,2})"?', s, re.IGNORECASE)
            if dem_m and rep_m:
                try:
                    return float(dem_m[0]), float(rep_m[0])
                except ValueError:
                    pass

    # 2. Recherche directe de la ligne "RCP Average" dans le HTML
    match_avg = re.search(r'RCP\s*Average.*?>\s*(\d{1,2}\.\d)\s*<.*?>\s*(\d{1,2}\.\d)', html, re.IGNORECASE | re.DOTALL)
    if match_avg:
        try:
            return float(match_avg.group(1)), float(match_avg.group(2))
        except ValueError:
            pass

    # 3. Mode secours textuel : isolation du premier bloc de nombres après "RCP Average"
    idx = html.find("RCP Average")
    if idx != -1:
        snippet = html[idx:idx+2000]
        numbers = re.findall(r'\b(\d{2}\.\d)\b', snippet)
        if len(numbers) >= 2:
            try:
                return float(numbers[0]), float(numbers[1])
            except ValueError:
                pass

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
                    d, r = parse_rcp_html(resp.text)
                    if d is not None and r is not None:
                        dem_val, rep_val = d, r
                        print(f"✅ [{code}] Extrait en direct RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception as e:
                print(f"⚠️ [{code}] Erreur d'accès à {url} : {e}")

        if dem_val is None or rep_val is None:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
            print(f"ℹ️ [{code}] Valeur de référence appliquée : DEM {dem_val}% / REP {rep_val}%")

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
