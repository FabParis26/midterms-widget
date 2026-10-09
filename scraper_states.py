import json
import re
import urllib.request
from datetime import datetime, timezone

# Liens directs vers chaque duel officiel de RealClearPolling
TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/texas/paxton-vs-talarico",
        "fallback_url": "https://www.realclearpolitics.com/epolls/2026/senate/tx/2026_texas_senate_cornyn_vs_talarico-8868.html",
        "default_dem": 45.0, "default_rep": 45.0
    },
    "IA": {
        "name": "Iowa",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/iowa/hinson-vs-turek",
        "default_dem": 47.0, "default_rep": 48.0
    },
    "ME": {
        "name": "Maine",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-jackson",
        "fallback_url": "https://www.realclearpolitics.com/epolls/2026/senate/me/2026_maine_senate_collins_vs_mills-8888.html",
        "default_dem": 46.0, "default_rep": 46.0
    },
    "OH": {
        "name": "Ohio",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/ohio/husted-vs-brown",
        "default_dem": 49.0, "default_rep": 45.0
    },
    "AK": {
        "name": "Alaska",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/alaska/sullivan-vs-peltola",
        "default_dem": 51.0, "default_rep": 49.0
    },
    "KS": {
        "name": "Kansas",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/kansas/marshall-vs-hamilton",
        "default_dem": 48.0, "default_rep": 45.0
    },
    "MI": {
        "name": "Michigan",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-elsayed",
        "default_dem": 48.0, "default_rep": 47.0
    },
    "NC": {
        "name": "Caroline du Nord",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/whatley-vs-cooper",
        "default_dem": 50.0, "default_rep": 43.0
    },
    "GA": {
        "name": "Géorgie",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/georgia/senate",
        "default_dem": 48.8, "default_rep": 46.5
    },
    "FL": {
        "name": "Floride",
        "url": "https://www.realclearpolling.com/polls/senate/general/2026/florida/moody-vs-nixon",
        "default_dem": 45.0, "default_rep": 47.0
    }
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

def extract_from_html(html):
    # 1. Extraction directe depuis le flux JSON Next.js embarqué
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

    # 2. Recherche par regex sur le tableau de moyenne HTML
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
        urls_to_try = [config["url"]]
        if "fallback_url" in config:
            urls_to_try.append(config["fallback_url"])

        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    dem_val, rep_val = extract_from_html(html)
                    if dem_val is not None and rep_val is not None:
                        print(f"✅ [{code}] En direct RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception as e:
                print(f"⚠️ [{code}] Erreur sur {url} : {e}")

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
