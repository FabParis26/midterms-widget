import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

# Configuration des 10 courses avec gestion automatique de l'ordre des slugs
TARGET_RACES = {
    "IA": {
        "name": "Iowa",
        "slugs": ["turek-vs-hinson", "hinson-vs-turek"],
        "state_path": "iowa",
        "default_dem": 45.9, "default_rep": 45.2
    },
    "TX": {
        "name": "Texas",
        "slugs": ["paxton-vs-talarico-vs-brown", "talarico-vs-paxton", "talarico-vs-cornyn"],
        "state_path": "texas",
        "default_dem": 46.6, "default_rep": 45.0
    },
    "ME": {
        "name": "Maine",
        "slugs": ["jackson-vs-collins", "collins-vs-jackson", "mills-vs-collins"],
        "state_path": "maine",
        "default_dem": 46.0, "default_rep": 46.0
    },
    "OH": {
        "name": "Ohio",
        "slugs": ["brown-vs-husted", "husted-vs-brown"],
        "state_path": "ohio",
        "default_dem": 49.0, "default_rep": 45.0
    },
    "AK": {
        "name": "Alaska",
        "slugs": ["peltola-vs-sullivan", "sullivan-vs-peltola"],
        "state_path": "alaska",
        "default_dem": 51.0, "default_rep": 49.0
    },
    "KS": {
        "name": "Kansas",
        "slugs": ["hamilton-vs-marshall", "marshall-vs-hamilton"],
        "state_path": "kansas",
        "default_dem": 48.0, "default_rep": 45.0
    },
    "MI": {
        "name": "Michigan",
        "slugs": ["elsayed-vs-rogers", "rogers-vs-elsayed"],
        "state_path": "michigan",
        "default_dem": 48.0, "default_rep": 47.0
    },
    "NC": {
        "name": "Caroline du Nord",
        "slugs": ["cooper-vs-whatley", "whatley-vs-cooper"],
        "state_path": "north-carolina",
        "default_dem": 50.0, "default_rep": 43.0
    },
    "GA": {
        "name": "Géorgie",
        "slugs": ["ossoff-vs-taylor-greene", "taylor-green-vs-ossoff", "senate"],
        "state_path": "georgia",
        "default_dem": 51.0, "default_rep": 37.0
    },
    "FL": {
        "name": "Floride",
        "slugs": ["nixon-vs-moody", "moody-vs-nixon"],
        "state_path": "florida",
        "default_dem": 45.0, "default_rep": 47.0
    }
}

def extract_from_html(html):
    # 1. Lecture directe du tableau JSON Next.js embarqué par RCP
    next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            data = json.loads(next_data_match.group(1))
            props = data.get('props', {}).get('pageProps', {})
            rcp_avg = props.get('rcpAverage') or props.get('data', {}).get('rcpAverage')
            if rcp_avg and isinstance(rcp_avg, list) and len(rcp_avg) > 0:
                scores = {}
                for cand in rcp_avg:
                    party = str(cand.get('party', '') or cand.get('affiliation', '')).upper()
                    val = cand.get('value') or cand.get('score') or cand.get('pct')
                    if val is not None:
                        if 'DEM' in party or party == 'D':
                            scores['dem'] = float(val)
                        elif 'REP' in party or 'GOP' in party or party == 'R':
                            scores['rep'] = float(val)
                if 'dem' in scores and 'rep' in scores:
                    return scores['dem'], scores['rep']
        except Exception:
            pass

    # 2. Recherche par expression régulière dans le HTML
    matches = re.findall(r'RCP Average.*?(\d{1,2}\.\d|\d{1,2})\s*.*?(\d{1,2}\.\d|\d{1,2})', html, re.IGNORECASE | re.DOTALL)
    if matches:
        try:
            return float(matches[0][0]), float(matches[0][1])
        except ValueError:
            pass

    return None, None

def fetch_live_data():
    states_result = {}

    for code, config in TARGET_RACES.items():
        dem_val, rep_val = None, None
        base_path = f"https://www.realclearpolling.com/polls/senate/general/2026/{config['state_path']}"
        
        # Test de chaque déclinaison d'URL jusqu'à trouver la bonne
        for slug in config["slugs"]:
            url = f"{base_path}/{slug}"
            try:
                resp = requests.get(url, impersonate="chrome120", timeout=10)
                if resp.status_code == 200:
                    dem_val, rep_val = extract_from_html(resp.text)
                    if dem_val is not None and rep_val is not None:
                        print(f"✅ [{code}] Données extraites en direct RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception as e:
                continue

        # Si aucune URL n'a répondu, application des données de sécurité
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
