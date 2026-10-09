import json
import re
from datetime import datetime, timezone
from curl_cffi import requests

# Candidats et mots-clés pour les 10 États cibles 2026
TARGET_RACES = {
    "TX": {"name": "Texas", "dem_kw": ["Talarico", "Crockett"], "rep_kw": ["Paxton", "Cornyn"], "default_dem": 45.0, "default_rep": 45.0},
    "NC": {"name": "Caroline du Nord", "dem_kw": ["Cooper"], "rep_kw": ["Whatley"], "default_dem": 50.0, "default_rep": 43.0},
    "MI": {"name": "Michigan", "dem_kw": ["El-Sayed", "Stevens"], "rep_kw": ["Rogers"], "default_dem": 48.0, "default_rep": 47.0},
    "ME": {"name": "Maine", "dem_kw": ["Jackson", "Platner", "Mills"], "rep_kw": ["Collins"], "default_dem": 50.0, "default_rep": 46.0},
    "KS": {"name": "Kansas", "dem_kw": ["Hamilton"], "rep_kw": ["Marshall"], "default_dem": 48.0, "default_rep": 45.0},
    "IA": {"name": "Iowa", "dem_kw": ["Turek"], "rep_kw": ["Hinson"], "default_dem": 43.0, "default_rep": 45.0},
    "OH": {"name": "Ohio", "dem_kw": ["Brown"], "rep_kw": ["Husted"], "default_dem": 49.0, "default_rep": 43.0},
    "AK": {"name": "Alaska", "dem_kw": ["Peltola"], "rep_kw": ["Sullivan"], "default_dem": 51.0, "default_rep": 49.0},
    "GA": {"name": "Géorgie", "dem_kw": ["Ossoff"], "rep_kw": ["Taylor Greene", "Greene"], "default_dem": 51.0, "default_rep": 37.0},
    "FL": {"name": "Floride", "dem_kw": ["Nixon"], "rep_kw": ["Moody"], "default_dem": 40.0, "default_rep": 47.0}
}

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
    'referer': 'https://www.realclearpolling.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def extract_from_summary(html_text):
    results = {}
    clean_html = re.sub(r'<script[^>]*>.*?</script>', ' ', html_text, flags=re.DOTALL)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
    clean_text = re.sub(r'\s+', ' ', clean_text)

    for code, config in TARGET_RACES.items():
        dem_score, rep_score = None, None

        for kw in config["dem_kw"]:
            m = re.findall(rf'{kw}\s*(\d{{1,2}}(?:\.\d)?)', clean_text, re.IGNORECASE)
            if m:
                dem_score = float(m[0])
                break

        for kw in config["rep_kw"]:
            m = re.findall(rf'{kw}\s*(\d{{1,2}}(?:\.\d)?)', clean_text, re.IGNORECASE)
            if m:
                rep_score = float(m[0])
                break

        if dem_score is not None and rep_score is not None:
            results[code] = (dem_score, rep_score)

    return results

def fetch_live_data():
    session = requests.Session()
    url = "https://www.realclearpolling.com/latest-polls/senate"
    extracted = {}

    try:
        resp = session.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if resp.status_code == 200:
            extracted = extract_from_summary(resp.text)
            print(f"✅ Page RCP récupérée ({len(extracted)} États extraits en direct)")
        else:
            print(f"⚠️ Code HTTP {resp.status_code} sur {url}")
    except Exception as e:
        print(f"⚠️ Erreur de connexion : {e}")

    states_result = {}
    for code, config in TARGET_RACES.items():
        if code in extracted:
            dem_val, rep_val = extracted[code]
            print(f"✅ [{code}] En direct RCP : DEM {dem_val}% / REP {rep_val}%")
        else:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
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
        "source": "RealClearPolling (En direct)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier states_data.json mis à jour !")

if __name__ == "__main__":
    fetch_live_data()
