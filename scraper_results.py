import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# On surveille les mêmes 10 courses clés pour l'instant
TARGET_RACES = {
    "GA": "Georgia",
    "MI": "Michigan",
    "NH": "New Hampshire",
    "ME": "Maine",
    "NC": "North Carolina",
    "OH": "Ohio",
    "TX": "Texas",
    "IA": "Iowa",
    "AK": "Alaska",
    "KS": "Kansas"
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
    except Exception as e:
        print(f"Erreur API Wikipedia: {e}")
    return ""

def parse_results(html_content):
    results = {}
    
    # Recherche du tableau "Summary of races" ou similaire
    tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    
    target_table = None
    for table in tables:
        # On cherche un tableau qui contient la liste des États
        if "Georgia" in table and "Texas" in table and "Incumbent" in table:
            target_table = table
            break
            
    if not target_table:
        print("Tableau de résultats introuvable sur la page (normal si l'élection n'a pas commencé).")
        return results

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', target_table, re.DOTALL | re.IGNORECASE)
    
    for row in rows:
        cells = re.findall(r'<(td|th)[^>]*>(.*?)</\1>', row, re.DOTALL | re.IGNORECASE)
        if not cells:
            continue
            
        clean_cells = [re.sub(r'<[^>]+>', '', c[1]).strip() for c in cells]
        
        # On essaie d'identifier la ligne d'un État cible
        state_code = None
        for code, name in TARGET_RACES.items():
            if len(clean_cells) > 0 and name in clean_cells[0]:
                state_code = code
                break
                
        if state_code:
            status = "tossup"
            note = "En attente des résultats"
            winner = ""
            
            # Logique d'analyse : on cherche des indicateurs de victoire D ou R
            # Sur Wikipedia, les lignes attribuées contiennent souvent "Hold" ou "Gain" ou une couleur spécifique.
            # Cette logique basique s'affinera le jour J selon la structure exacte du tableau.
            row_text = " ".join(clean_cells).lower()
            
            if "democratic hold" in row_text or "democratic gain" in row_text or "democrat hold" in row_text:
                 status = "called_dem"
                 winner = "Démocrate déclaré"
            elif "republican hold" in row_text or "republican gain" in row_text:
                 status = "called_rep"
                 winner = "Républicain déclaré"
            elif "too close to call" in row_text or "tossup" in row_text:
                status = "tossup"
                note = "Scrutin très serré"
            else:
                 # Si rien n'est explicite, on laisse en attente
                 pass

            results[state_code] = {
                "status": status,
                "note": note
            }
            if winner:
                results[state_code]["winner"] = winner

    return results

def main():
    print("Connexion à l'API Wikipedia pour les résultats du Sénat...")
    
    # La page principale des élections sénatoriales
    html = fetch_wiki_html("2026_United_States_Senate_elections")
    
    parsed_results = parse_results(html)
    
    # On prépare le dictionnaire de sortie
    output_results = {}
    
    # Pour chaque État cible, on prend le résultat trouvé, sinon on met par défaut
    for code, name in TARGET_RACES.items():
        if code in parsed_results:
            output_results[code] = parsed_results[code]
        else:
             output_results[code] = { "status": "tossup", "note": "En attente" }

    # Comptage des sièges de base (ceux qui ne sont pas en élection en 2026)
    # 32 Démocrates (incluant les indépendants s'alignant avec eux) et 33 Républicains
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "baseline_dem": 32, 
        "baseline_rep": 33,
        "results": output_results
    }

    with open("results_senate.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Fichier results_senate.json mis à jour avec succès !")

if __name__ == "__main__":
    main()
