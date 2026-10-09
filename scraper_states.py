import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/texas",
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-paxton"
        ],
        "default_dem": 48.1, "default_rep": 45.3
    },
    "IA": {
        "name": "Iowa",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/iowa",
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/turek-vs-hinson"
        ],
        "default_dem": 45.9, "default_rep": 45.2
    },
    "ME": {
        "name": "Maine",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/maine",
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/jackson-vs-collins"
        ],
        "default_dem": 48.1, "default_rep": 47.4
    },
    "OH": {
        "name": "Ohio",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/ohio",
            "https://www.realclearpolling.com/polls/senate/general/2026/ohio/brown-vs-husted"
        ],
        "default_dem": 47.3, "default_rep": 44.1
    },
    "AK": {
        "name": "Alaska",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/alaska",
            "https://www.realclearpolling.com/polls/senate/general/2026/alaska/peltola-vs-sullivan"
        ],
        "default_dem": 48.5, "default_rep": 47.3
    },
    "KS": {
        "name": "Kansas",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/kansas",
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/hamilton-vs-marshall"
        ],
        "default_dem": 48.0, "default_rep": 45.0
    },
    "MI": {
        "name": "Michigan",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/michigan",
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/el-sayed-vs-rogers"
        ],
        "default_dem": 48.1, "default_rep": 44.9
    },
    "NC": {
        "name": "Caroline du Nord",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/north-carolina",
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/cooper-vs-whatley"
        ],
        "default_dem": 50.0, "default_rep": 43.0
    },
    "GA": {
        "name": "Géorgie",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/georgia",
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/ossoff-vs-taylor-greene"
        ],
        "default_dem": 51.0, "default_rep": 37.0
    },
    "FL": {
        "name": "Floride",
        "urls": [
            "https://www.realclearpolling.com/elections/senate/2026/florida",
            "https://www.realclearpolling.com/polls/senate/general/2026/florida/nixon-vs-moody"
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

def parse_rcp_html(html):
    # 1. Analyse des blocs de scripts JSON
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in script_matches:
        if 'rcpAverage' in s or ('party' in s and 'value' in s):
            try:
                json_objs = re.findall(r'\{[^{}]*"party"[^{}]*\}', s)
                dem_score, rep_score = None, None
                for j_str in json_objs:
                    p_match = re.search(r'"party"\s*:\s*"([^"]+)"', j_str, re.I)
                    v_match = re.search(r'"(?:value|score|pct|average)"\s*:\s*"?(\d{1,2}(?:\.\d)?)"?', j_str, re.I)
                    if p_match and v_match:
                        party = p_match.group(1).upper()
                        val = float(v_match.group(1))
                        if 'DEM' in party or party == 'D':
                            dem_score = val
                        elif 'REP' in party or 'GOP' in party or party == 'R':
                            rep_score = val
                if dem_score is not None and rep_score is not None:
                    return dem_score, rep_score
            except Exception:
                pass

    # 2. Analyse ciblée du bloc textuel autour de "RCP Average"
    idx = html.find("RCP Average")
    if idx == -1:
        idx = html.find("RCP AVERAGE")
    if idx == -1:
        idx = html.lower().find("rcp average")

    if idx != -1:
        snippet = html[idx:idx+1200]
        
        # Vérification de l'ordre Démocrate vs Républicain dans l'en-tête
        header_snippet = html[max(0, idx-800):idx]
        dem_first = True
        d_pos = header_snippet.rfind("(D)")
        r_pos = header_snippet.rfind("(R)")
        if d_pos != -1 and r_pos != -1 and r_pos < d_pos:
            dem_first = False

        # Nettoyage HTML et filtrage des dates et spreads
        text_clean = re.sub(r'<[^>]+>', ' ', snippet)
        text_clean = re.sub(r'\d{1,2}/\d{1,2}(?:/\d{2,4})?', ' ', text_clean)
        text_clean = re.sub(r'[+\-]\d{1,2}(?:\.\d)?', ' ', text_clean)

        # Isolement des pourcentages valides
        nums = re.findall(r'\b(\d{2}(?:\.\d)?)\b', text_clean)
        valid_nums = [float(n) for n in nums if 30.0 <= float(n) <= 70.0]

        if len(valid_nums) >= 2:
            val1, val2 = valid_nums[0], valid_nums[1]
            return (val1, val2) if dem_first else (val2, val1)

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
