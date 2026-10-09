import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

TARGET_STATES = {
    "TX": {"name": "Texas", "slug": "texas"},
    "NC": {"name": "Caroline du Nord", "slug": "north-carolina"},
    "MI": {"name": "Michigan", "slug": "michigan"},
    "ME": {"name": "Maine", "slug": "maine"},
    "KS": {"name": "Kansas", "slug": "kansas"},
    "IA": {"name": "Iowa", "slug": "iowa"},
    "OH": {"name": "Ohio", "slug": "ohio"},
    "AK": {"name": "Alaska", "slug": "alaska"},
    "GA": {"name": "Géorgie", "slug": "georgia"},
    "FL": {"name": "Floride", "slug": "florida"}
}

HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def extract_270towin(html):
    clean_text = re.sub(r'<[^>]+>', ' ', html)
    clean_text = re.sub(r'\s+', ' ', clean_text)

    # Détection des scores Démocrate (D) et Républicain (R)
    dem_match = re.search(r'(?:Democrat|DEM|\(D\))\s*[:\s]*(\d{1,2}\.\d|\d{1,2})\s*%?', clean_text, re.IGNORECASE)
    rep_match = re.search(r'(?:Republican|REP|GOP|\(R\))\s*[:\s]*(\d{1,2}\.\d|\d{1,2})\s*%?', clean_text, re.IGNORECASE)

    if dem_match and rep_match:
        try:
            return float(dem_match.group(1)), float(rep_match.group(1))
        except ValueError:
            pass

    # Alternative : isolation des pourcentages de sondages valides
    nums = re.findall(r'\b(\d{2}\.\d)\b', clean_text)
    valid_nums = [float(n) for n in nums if 25.0 <= float(n) <= 75.0]
    if len(valid_nums) >= 2:
        return valid_nums[0], valid_nums[1]

    return None, None

def fetch_live_data():
    session = requests.Session()
    states_result = {}

    for code, config in TARGET_STATES.items():
        url = f"https://www.270towin.com/2026-senate-election/{config['slug']}"
        dem_val, rep_val = None, None

        try:
            resp = session.get(url, headers=HEADERS, impersonate="chrome120", timeout=10)
            if resp.status_code == 200:
                d, r = extract_270towin(resp.text)
                if d is not None and r is not None:
                    dem_val, rep_val = d, r
                    print(f"✅ [{code}] En direct 270ToWin : DEM {dem_val}% / REP {rep_val}%")
                else:
                    print(f"⚠️ [{code}] Page accessible mais valeurs non isolées sur {url}")
            else:
                print(f"⚠️ [{code}] Code HTTP {resp.status_code}")
        except Exception as e:
            print(f"⚠️ [{code}] Erreur : {e}")

        if dem_val is None or rep_val is None:
            dem_val, rep_val = 48.0, 48.0
            print(f"ℹ️ [{code}] Valeur de secours appliquée")

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
        "source": "270ToWin (En direct)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier states_data.json mis à jour !")

if __name__ == "__main__":
    fetch_live_data()
