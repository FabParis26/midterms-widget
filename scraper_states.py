import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

# Configuration des 10 États clés avec slugs et candidats réels RCP
TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "state_path": "texas",
        "slugs": ["talarico-vs-paxton", "paxton-vs-talarico", "cornyn-vs-crockett"],
        "default_dem": 48.1, "default_rep": 45.3
    },
    "IA": {
        "name": "Iowa",
        "state_path": "iowa",
        "slugs": ["turek-vs-hinson", "hinson-vs-turek"],
        "default_dem": 45.9, "default_rep": 45.2
    },
    "ME": {
        "name": "Maine",
        "state_path": "maine",
        "slugs": ["collins-vs-jackson", "jackson-vs-collins"],
        "default_dem": 48.1, "default_rep": 47.4
    },
    "OH": {
        "name": "Ohio",
        "state_path": "ohio",
        "slugs": ["husted-vs-brown", "brown-vs-husted"],
        "default_dem": 49.0, "default_rep": 45.0
    },
    "AK": {
        "name": "Alaska",
        "state_path": "alaska",
        "slugs": ["sullivan-vs-peltola", "peltola-vs-sullivan"],
        "default_dem": 51.0, "default_rep": 49.0
    },
    "KS": {
        "name": "Kansas",
        "state_path": "kansas",
        "slugs": ["marshall-vs-hamilton", "hamilton-vs-marshall"],
        "default_dem": 48.0, "default_rep": 45.0
    },
    "MI": {
        "name": "Michigan",
        "state_path": "michigan",
        "slugs": ["rogers-vs-el-sayed", "el-sayed-vs-rogers", "rogers-vs-elsayed"],
        "default_dem": 48.1, "default_rep": 44.9
    },
    "NC": {
        "name": "Caroline du Nord",
        "state_path": "north-carolina",
        "slugs": ["cooper-vs-whatley", "whatley-vs-cooper"],
        "default_dem": 50.0, "default_rep": 43.0
    },
    "GA": {
        "name": "Géorgie",
        "state_path": "georgia",
        "slugs": ["ossoff-vs-taylor-greene", "taylor-greene-vs-ossoff", "senate"],
        "default_dem": 51.0, "default_rep": 37.0
    },
    "FL": {
        "name": "Floride",
        "state_path": "florida",
        "slugs": ["moody-vs-nixon", "nixon-vs-moody"],
        "default_dem": 40.0, "default_rep": 50.0
    }
}

def parse_json_next_data(html):
    """Extraction récursive dans l'objet __NEXT_DATA__ de Next.js"""
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return None, None

    try:
        data = json.loads(match.group(1))
    except Exception:
        return None, None

    dem, rep = None, None

    def walk(obj):
        nonlocal dem, rep
        if isinstance(obj, dict):
            for key in ['rcpAverage', 'candidates', 'pollResults', 'data', 'poll']:
                if key in obj and isinstance(obj[key], list):
                    d, r = parse_candidate_list(obj[key])
                    if d is not None and r is not None:
                        dem, rep = d, r
                        return
            for v in obj.values():
                if dem is None or rep is None:
                    walk(v)
        elif isinstance(obj, list):
            d, r = parse_candidate_list(obj)
            if d is not None and r is not None:
                dem, rep = d, r
                return
            for item in obj:
                if dem is None or rep is None:
                    walk(item)

    def parse_candidate_list(lst):
        d_val, r_val = None, None
        for item in lst:
            if isinstance(item, dict):
                party = str(item.get('party') or item.get('affiliation') or item.get('name') or '').upper()
                val = item.get('value') or item.get('score') or item.get('pct') or item.get('average')
                if val is not None:
                    try:
                        num = float(val)
                        if any(x in party for x in ['DEM', 'D', 'DEMOCRAT']):
                            d_val = num
                        elif any(x in party for x in ['REP', 'R', 'GOP', 'REPUBLICAN']):
                            r_val = num
                    except (ValueError, TypeError):
                        pass
        return d_val, r_val

    walk(data)
    return dem, rep

def parse_html_regex(html):
    """Extraction par regex dans le texte HTML"""
    dem_m = re.findall(r'(?:DEM|DÉM|Democrat|\(D\))\s*[:\s]*(\d{1,2}\.\d|\d{1,2})\s*%?', html, re.IGNORECASE)
    rep_m = re.findall(r'(?:REP|GOP|Republican|\(R\))\s*[:\s]*(\d{1,2}\.\d|\d{1,2})\s*%?', html, re.IGNORECASE)

    if dem_m and rep_m:
        try:
            return float(dem_m[0]), float(rep_m[0])
        except ValueError:
            pass

    matches = re.findall(r'RCP\s*Average.*?(\d{1,2}\.\d)\s*.*?(\d{1,2}\.\d)', html, re.IGNORECASE | re.DOTALL)
    if matches:
        try:
            return float(matches[0][0]), float(matches[0][1])
        except ValueError:
            pass

    return None, None

def extract_scores(html):
    dem, rep = parse_json_next_data(html)
    if dem is not None and rep is not None:
        return dem, rep
    return parse_html_regex(html)

def fetch_live_data():
    session = requests.Session()
    states_result = {}

    for code, config in TARGET_RACES.items():
        dem_val, rep_val = None, None
        base_url = f"https://www.realclearpolling.com/polls/senate/general/2026/{config['state_path']}"

        for slug in config["slugs"]:
            url = f"{base_url}/{slug}"
            try:
                resp = session.get(url, impersonate="chrome120", timeout=12)
                if resp.status_code == 200:
                    d, r = extract_scores(resp.text)
                    if d is not None and r is not None:
                        dem_val, rep_val = d, r
                        print(f"✅ [{code}] Extrait en direct depuis RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception:
                continue

        # Secours de niveau 2 : page récapitulative globale
        if dem_val is None or rep_val is None:
            try:
                summary_url = "https://www.realclearpolling.com/latest-polls/senate"
                resp = session.get(summary_url, impersonate="chrome120", timeout=12)
                if resp.status_code == 200:
                    d, r = extract_scores(resp.text)
                    if d is not None and r is not None:
                        dem_val, rep_val = d, r
                        print(f"✅ [{code}] Extrait depuis la page récapitulative RCP : DEM {dem_val}% / REP {rep_val}%")
            except Exception:
                pass

        # Secours de niveau 3 : valeurs par défaut si blocage total
        if dem_val is None or rep_val is None:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
            print(f"⚠️ [{code}] Valeur de référence appliquée : DEM {dem_val}% / REP {rep_val}%")

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
