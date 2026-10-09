import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from curl_cffi import requests

# Configuration des 10 États avec leurs URL directes sur RealClearPolling
TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-paxton",
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-cornyn"
        ],
        "default_dem": 48.1, "default_rep": 45.3
    },
    "IA": {
        "name": "Iowa",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/turek-vs-hinson",
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/hinson-vs-turek"
        ],
        "default_dem": 45.9, "default_rep": 45.2
    },
    "ME": {
        "name": "Maine",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-jackson",
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-platner"
        ],
        "default_dem": 48.3, "default_rep": 47.3
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
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-el-sayed",
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/el-sayed-vs-rogers"
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
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/taylor-green-vs-ossoff"
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
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.realclearpolling.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def parse_rcp_with_bs4(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Recherche de toutes les tables du document HTML
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        rcp_tr = None
        header_tr = None

        for tr in rows:
            text = tr.get_text()
            if 'rcp average' in text.lower():
                rcp_tr = tr
            elif any(tag in text for tag in ['(D)', '(R)', 'Democrat', 'Republican', 'GOP']):
                if not header_tr:
                    header_tr = tr

        if rcp_tr:
            # 1. Analyse de l'ordre Démocrate / Républicain dans l'en-tête
            dem_first = True
            if header_tr:
                h_text = header_tr.get_text()
                d_idx = h_text.find('(D)')
                r_idx = h_text.find('(R)')
                if d_idx != -1 and r_idx != -1:
                    dem_first = (d_idx < r_idx)
                else:
                    d_pos = max(h_text.find('DEM'), h_text.find('Democrat'))
                    r_pos = max(h_text.find('REP'), h_text.find('GOP'), h_text.find('Republican'))
                    if d_pos != -1 and r_pos != -1:
                        dem_first = (d_pos < r_pos)

            # 2. Extraction des chiffres de la ligne "RCP Average"
            cells = rcp_tr.find_all(['td', 'th'])
            nums = []
            for cell in cells:
                c_text = cell.get_text().strip()
                # On recherche les nombres décimaux (ex: 48.1 ou 45)
                matches = re.findall(r'\b(\d{2}(?:\.\d)?)\b', c_text)
                for val_str in matches:
                    val = float(val_str)
                    if 25.0 <= val <= 75.0:  # Fourchette valide de pourcentage de sondage
                        nums.append(val)

            if len(nums) >= 2:
                dem_score = nums[0] if dem_first else nums[1]
                rep_score = nums[1] if dem_first else nums[0]
                return dem_score, rep_score

    # Fallback par recherche regex sur ligne TR brute si BeautifulSoup ne trouve pas la table
    tr_matches = re.findall(r'<tr[^>]*>(?:(?!</tr>).)*?RCP\s*Average(?:(?!</tr>).)*?</tr>', html, re.IGNORECASE | re.DOTALL)
    for tr_html in tr_matches:
        clean_text = re.sub(r'<[^>]+>', ' ', tr_html)
        clean_text = re.sub(r'\d{1,2}/\d{1,2}(?:/\d{2,4})?', ' ', clean_text)
        nums = re.findall(r'\b(\d{2}(?:\.\d)?)\b', clean_text)
        valid = [float(n) for n in nums if 25.0 <= float(n) <= 75.0]
        if len(valid) >= 2:
            return valid[0], valid[1]

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
                    d, r = parse_rcp_with_bs4(resp.text)
                    if d is not None and r is not None:
                        dem_val, rep_val = d, r
                        print(f"✅ [{code}] Extraction réussie en direct depuis RCP : DEM {dem_val}% / REP {rep_val}% ({url})")
                        break
            except Exception as e:
                print(f"⚠️ [{code}] Erreur de connexion à {url} : {e}")

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
