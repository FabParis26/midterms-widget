import json
import re
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone

# Les 10 batailles sénatoriales cibles de 2026
TARGET_RACES = {
    "GA": {"name": "Géorgie", "wiki_page": "2026_United_States_Senate_election_in_Georgia", "dem_kw": "Ossoff", "rep_kw": "Greene"},
    "MI": {"name": "Michigan", "wiki_page": "2026_United_States_Senate_election_in_Michigan", "dem_kw": "El-Sayed", "rep_kw": "Rogers"},
    "NH": {"name": "New Hampshire", "wiki_page": "2026_United_States_Senate_election_in_New_Hampshire", "dem_kw": "Pappas", "rep_kw": "Sununu"},
    "ME": {"name": "Maine", "wiki_page": "2026_United_States_Senate_election_in_Maine", "dem_kw": "Jackson", "rep_kw": "Collins"},
    "NC": {"name": "Caroline du Nord", "wiki_page": "2026_United_States_Senate_election_in_North_Carolina", "dem_kw": "Cooper", "rep_kw": "Whatley"},
    "OH": {"name": "Ohio", "wiki_page": "2026_United_States_Senate_special_election_in_Ohio", "dem_kw": "Brown", "rep_kw": "Husted"},
    "TX": {"name": "Texas", "wiki_page": "2026_United_States_Senate_election_in_Texas", "dem_kw": "Talarico", "rep_kw": "Paxton"},
    "IA": {"name": "Iowa", "wiki_page": "2026_United_States_Senate_election_in_Iowa", "dem_kw": "Turek", "rep_kw": "Hinson"},
    "AK": {"name": "Alaska", "wiki_page": "2026_United_States_Senate_election_in_Alaska", "dem_kw": "Peltola", "rep_kw": "Sullivan"},
    "KS": {"name": "Kansas", "wiki_page": "2026_United_States_Senate_election_in_Kansas", "dem_kw": "Hamilton", "rep_kw": "Marshall"}
}

HEADERS = {'User-Agent': 'MidtermsWidget/1.1 (https://github.com/fabparis26/midterms-widget)'}
FILEPATH = "states_data.json"

def load_previous_data():
    """Charge le fichier JSON existant pour servir de secours."""
    if os.path.exists(FILEPATH):
        try:
            with open(FILEPATH, "r", encoding="utf-8") as f:
                return json.load(f).get("states", {})
        except Exception as e:
            print(f"Impossible de lire l'historique : {e}")
    return {}

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
            dem_scores = []
            rep_scores = []
            
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
                            dem_scores.append(d_val)
                            rep_scores.append(r_val)
                            if len(dem_scores) == 3:
                                break
                                
            if dem_scores and rep_scores:
                avg_dem = round(sum(dem_scores) / len(dem_scores), 1)
                avg_rep = round(sum(rep_scores) / len(rep_scores), 1)
                return avg_dem, avg_rep
                
    return None, None

def fetch_live_data():
    states_result = {}
    print("Connexion à l'API Wikipedia...")
    
    previous_data = load_previous_data()

    for code, config in TARGET_RACES.items():
        state_html = fetch_wiki_html(config["wiki_page"])
        dem_val, rep_val = parse_wikitable_poll(state_html, config["dem_kw"], config["rep_kw"])

        if dem_val is not None and rep_val is not None:
            print(f"[{code}] Extrait via Wikipedia : DEM {dem_val}% / REP {rep_val}%")
        elif code in previous_data:
            dem_val = previous_data[code]["dem"]
            rep_val = previous_data[code]["rep"]
            print(f"[{code}] Échec Wikipedia -> Restauration des données précédentes : DEM {dem_val}% / REP {rep_val}%")
        else:
            dem_val = 50.0
            rep_val = 50.0
            print(f"[{code}] Aucune donnée disponible, égalité appliquée par défaut.")

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
        "source": "Instituts de sondages (via Wikipedia)",
        "states": states_result
    }

    with open(FILEPATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Fichier {FILEPATH} mis à jour avec succès.")

if __name__ == "__main__":
    fetch_live_data()
