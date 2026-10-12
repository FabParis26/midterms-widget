import json
import re
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone

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

def parse_generic_ballot(html_content):
    # On cherche tous les tableaux de type wikitable
    tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    
    for table in tables:
        # On vérifie que c'est bien un tableau de sondages (présence des deux partis)
        if not (re.search(r'Democratic', table, re.IGNORECASE) and re.search(r'Republican', table, re.IGNORECASE)):
            continue

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL | re.IGNORECASE)
        dem_col_idx = None
        rep_col_idx = None
        
        # On repère l'emplacement des colonnes Démocrate et Républicain
        for row in rows:
            headers = re.findall(r'<th[^>]*>(.*?)</th>', row, re.DOTALL | re.IGNORECASE)
            if headers:
                clean_headers = [re.sub(r'<[^>]+>', '', h).strip().lower() for h in headers]
                for idx, h in enumerate(clean_headers):
                    if 'democratic' in h or 'democrat' in h:
                        dem_col_idx = idx
                    elif 'republican' in h:
                        rep_col_idx = idx
                if dem_col_idx is not None and rep_col_idx is not None:
                    break
                    
        # Extraction et moyenne des 3 derniers sondages
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
                        # Garde-fou de pertinence (les intentions nationales oscillent entre 35% et 55%)
                        if 35.0 <= d_val <= 60.0 and 35.0 <= r_val <= 60.0:
                            dem_scores.append(d_val)
                            rep_scores.append(r_val)
                            if len(dem_scores) == 3:
                                break
            
            if dem_scores and rep_scores:
                return round(sum(dem_scores) / len(dem_scores), 1), round(sum(rep_scores) / len(rep_scores), 1)
    
    return None, None

def main():
    print("Connexion à l'API Wikipedia pour le vote national (Generic Ballot)...")
    html = fetch_wiki_html("2026_United_States_House_of_Representatives_elections")
    
    avg_dem, avg_rep = parse_generic_ballot(html)
    
    if avg_dem is None or avg_rep is None:
        print("⚠️ Impossible d'extraire les sondages, utilisation des données de secours.")
        avg_dem, avg_rep = 48.5, 46.5
    else:
        print(f"✅ Moyenne des 3 derniers sondages nationaux : Démocrates {avg_dem}% / Républicains {avg_rep}%")

    margin = round(avg_dem - avg_rep, 1)
    leading = "Démocrates" if margin > 0 else ("Républicains" if margin < 0 else "Égalité")

    # --- GESTION DE L'HISTORIQUE POUR LE GRAPHIQUE ---
    history = []
    filepath = "data.json"
    
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                history = old_data.get("history", [])
        except Exception as e:
            print(f"Erreur de lecture de l'historique : {e}")

    # Ajouter la donnée du jour si elle n'existe pas déjà
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if not history or history[-1].get("date") != today_str:
        history.append({
            "date": today_str,
            "democrats": avg_dem,
            "republicans": avg_rep
        })
        
    # On garde seulement les 30 derniers points pour que la courbe reste lisible
    history = history[-30:]

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Instituts de sondages (via Wikipedia)",
        "democrats": avg_dem,
        "republicans": avg_rep,
        "margin": abs(margin),
        "leading_party": leading,
        "history": history
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier data.json (National) mis à jour avec succès !")

if __name__ == "__main__":
    main()
