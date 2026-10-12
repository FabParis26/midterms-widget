import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TARGET_RACES = {
    "TX": {"name": "Texas", "wiki_page": "2026_United_States_Senate_election_in_Texas", "dem_kw": "Talarico", "rep_kw": "Paxton", "default_dem": 48.1, "default_rep": 45.3},
    "NC": {"name": "Caroline du Nord", "wiki_page": "2026_United_States_Senate_election_in_North_Carolina", "dem_kw": "Cooper", "rep_kw": "Whatley", "default_dem": 49.8, "default_rep": 41.0},
    "MI": {"name": "Michigan", "wiki_page": "2026_United_States_Senate_election_in_Michigan", "dem_kw": "El-Sayed", "rep_kw": "Rogers", "default_dem": 48.1, "default_rep": 44.9},
    "ME": {"name": "Maine", "wiki_page": "2026_United_States_Senate_election_in_Maine", "dem_kw": "Jackson", "rep_kw": "Collins", "default_dem": 47.5, "default_rep": 46.8},
    "KS": {"name": "Kansas", "wiki_page": "2026_United_States_Senate_election_in_Kansas", "dem_kw": "Hamilton", "rep_kw": "Marshall", "default_dem": 45.4, "default_rep": 45.6},
    "IA": {"name": "Iowa", "wiki_page": "2026_United_States_Senate_election_in_Iowa", "dem_kw": "Turek", "rep_kw": "Hinson", "default_dem": 45.9, "default_rep": 45.2},
    "OH": {"name": "Ohio", "wiki_page": "2026_United_States_Senate_election_in_Ohio", "dem_kw": "Brown", "rep_kw": "Husted", "default_dem": 47.3, "default_rep": 44.1},
    "AK": {"name": "Alaska", "wiki_page": "2026_United_States_Senate_election_in_Alaska", "dem_kw": "Peltola", "rep_kw": "Sullivan", "default_dem": 48.5, "default_rep": 47.3},
    "GA": {"name": "Géorgie", "wiki_page": "2026_United_States_Senate_election_in_Georgia", "dem_kw": "Ossoff", "rep_kw": "Greene", "default_dem": 51.0, "default_rep": 37.0},
    "FL": {"name": "Floride", "wiki_page": "2026_United_States_Senate_election_in_Florida", "dem_kw": "Nixon", "rep_kw": "Moody", "default_dem": 40.0, "default_rep": 47.0}
}

HEADERS = {'User-Agent': 'MidtermsWidget/1.0 (https://github.com/fabparis26/midterms-widget)'}

def fetch_wiki_html(page_title):
    api_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page_title)}&format=json&prop=text"
    req = urllib.request.Request(api_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if 'parse' in data and 'text' in data['parse']:
                return data['parse']['text']['*']
    except Exception:
        pass
    return ""

def parse_wikitable_poll(html_content, dem_kw, rep_kw):
    tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL | re.IGNORECASE)
        if not rows:
            continue
            
        dem_col_idx = None
        rep_col_idx = None
        
        for row in rows:
            headers = re.findall(r'<th[^>]*>(.*?)</th>', row, re.DOTALL | re.IGNORECASE)
            if headers:
                clean_headers = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
                for idx, h in enumerate(clean_headers):
                    if dem_kw.lower() in h.lower():
                        dem_col_idx = idx
                    elif rep_kw.lower() in h.lower():
                        rep_col_idx = idx
                if dem_col_idx is not None and rep_col_idx is not None:
                    break
                    
        if dem_col_idx is not None and rep_col_idx is not None:
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if len(cells) > max(dem_col_idx, rep_col_idx):
                    d_text = re.sub(r'<[^>]+>', '', cells[dem_col_idx]).strip()
                    r_text = re.sub(r'<[^>]+>', '', cells[rep_col_idx]).strip()
                    
                    d_match = re.search(r'\b(\d{2}(?:\.\d)?)\b', d_text)
                    r_match = re.search(r'\b(\d{2}(?:\.\d)?)\b', r_text)
                    
                    if d_match and r_match:
                        d_val = float(d_match.group(1))
                        r_val = float(r_match.group(1))
                        if 20.0 <= d_val <= 80.0 and 20.0 <= r_val <= 80.0:
                            return d_val, r_val
    return None, None

def fetch_live_data():
    states_result = {}
    print("Connexion à l'API Wikipedia...")

    for code, config in TARGET_RACES.items():
        state_html = fetch_wiki_html(config["wiki_page"])
        dem_val, rep_val = parse_wikitable_poll(state_html, config["dem_kw"], config["rep_kw"])

        if dem_val is not None and rep_val is not None:
            print(f"✅ [{code}] Extrait de la wikitable Wikipedia : DEM {dem_val}% / REP {rep_val}%")
        else:
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
        "source": "Wikipedia API (Tableaux de sondages)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier states_data.json généré avec succès !")

if __name__ == "__main__":
    fetch_live_data()
