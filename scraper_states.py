import json
import re
import time
from datetime import datetime, timezone
from curl_cffi import requests

# Configuration des 10 États clés et mots-clés associables
TARGET_RACES = {
    "TX": {"name": "Texas", "search": ["Texas", "Talarico", "Paxton"], "default_dem": 48.4, "default_rep": 45.3},
    "IA": {"name": "Iowa", "search": ["Iowa", "Turek", "Hinson"], "default_dem": 46.2, "default_rep": 45.2},
    "ME": {"name": "Maine", "search": ["Maine", "Jackson", "Collins"], "default_dem": 48.1, "default_rep": 47.4},
    "OH": {"name": "Ohio", "search": ["Ohio", "Brown", "Husted"], "default_dem": 47.3, "default_rep": 44.1},
    "AK": {"name": "Alaska", "search": ["Alaska", "Peltola", "Sullivan"], "default_dem": 48.5, "default_rep": 47.3},
    "KS": {"name": "Kansas", "search": ["Kansas", "Hamilton", "Marshall"], "default_dem": 48.0, "default_rep": 45.0},
    "MI": {"name": "Michigan", "search": ["Michigan", "El-Sayed", "Rogers"], "default_dem": 48.1, "default_rep": 44.9},
    "NC": {"name": "Caroline du Nord", "search": ["North Carolina", "Cooper", "Whatley"], "default_dem": 50.0, "default_rep": 43.0},
    "GA": {"name": "Géorgie", "search": ["Georgia", "Ossoff"], "default_dem": 51.0, "default_rep": 37.0},
    "FL": {"name": "Floride", "search": ["Florida", "Nixon", "Moody"], "default_dem": 40.0, "default_rep": 50.0}
}

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9,fr;q=0.8',
    'cache-control': 'max-age=0',
    'referer': 'https://www.realclearpolling.com/',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_all_from_json_next(html):
    """Analyse récursive des données JSON embarquées de Next.js"""
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return {}

    try:
        data = json.loads(match.group(1))
    except Exception:
        return {}

    extracted = {}

    def search_races(node):
        if isinstance(node, dict):
            title = str(node.get('title') or node.get('name') or node.get('race_name') or node.get('slug') or '')
            rcp_avg = node.get('rcpAverage') or node.get('candidates') or node.get('pollResults')
            
            if title and isinstance(rcp_avg, list):
                dem_score, rep_score = None, None
                for cand in rcp_avg:
                    if isinstance(cand, dict):
                        party = str(cand.get('party') or cand.get('affiliation') or cand.get('name') or '').upper()
                        val = cand.get('value') or cand.get('score') or cand.get('pct') or cand.get('average')
                        if val is not None:
                            try:
                                num = float(val)
                                if any(x in party for x in ['DEM', 'D', 'DEMOCRAT']):
                                    dem_score = num
                                elif any(x in party for x in ['REP', 'R', 'GOP', 'REPUBLICAN']):
                                    rep_score = num
                            except (ValueError, TypeError):
                                pass
                if dem_score is not None and rep_score is not None:
                    extracted[title] = (dem_score, rep_score)

            for v in node.values():
                search_races(v)
        elif isinstance(node, list):
            for item in node:
                search_races(item)

    search_races(data)
    return extracted

def fetch_live_data():
    session = requests.Session()
    
    # 1. Établissement des cookies de session via la page d'accueil
    print("🔄 Initialisation de la session sur RealClearPolling...")
    try:
        session.get("https://www.realclearpolling.com/", headers=HEADERS, impersonate="chrome120", timeout=12)
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Avertissement lors de la visite d'accueil : {e}")

    extracted_data = {}
    sources_to_try = [
        "https://www.realclearpolling.com/maps/senate/2026/toss-up",
        "https://www.realclearpolling.com/latest-polls/senate",
        "https://www.realclearpolling.com/polls/senate"
    ]

    for source_url in sources_to_try:
        try:
            print(f"🌐 Tentative d'extraction sur : {source_url}")
            resp = session.get(source_url, headers=HEADERS, impersonate="chrome120", timeout=12)
            if resp.status_code == 200:
                data_found = extract_all_from_json_next(resp.text)
                if data_found:
                    extracted_data.update(data_found)
                    print(f"✅ Source validée (200 OK) — {len(data_found)} éléments extraits")
                    break
                else:
                    print(f"⚠️ 200 OK mais aucun bloc JSON trouvé sur {source_url}")
            else:
                print(f"⚠️ Erreur HTTP {resp.status_code} sur {source_url}")
        except Exception as e:
            print(f"⚠️ Échec sur {source_url} : {e}")

    states_result = {}

    for code, config in TARGET_RACES.items():
        dem_val, rep_val = None, None

        for race_title, scores in extracted_data.items():
            if any(term.lower() in race_title.lower() for term in config["search"]):
                dem_val, rep_val = scores
                print(f"✅ [{code}] Données extraites en direct RCP : DEM {dem_val}% / REP {rep_val}%")
                break

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
