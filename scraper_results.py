import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Les 35 scrutins sénatoriaux en jeu en 2026 (33 Classe 2 + 2 spéciales)
ALL_SENATE_RACES_2026 = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AR": "Arkansas",
    "CO": "Colorado",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "ID": "Idaho",
    "IL": "Illinois",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MT": "Montana",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NC": "North Carolina",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "VA": "Virginia",
    "WV": "West Virginia",
    "WY": "Wyoming"
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
        print(f"Erreur API Wikipedia : {e}")
    return ""

def parse_results(html_content):
    results = {}
    tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    
    target_table = None
    for table in tables:
        if "Georgia" in table and "Texas" in table and "Incumbent" in table:
            target_table = table
            break
            
    if not target_table:
        print("Tableau de résultats introuvable sur la page (normal avant l'élection).")
        return results

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', target_table, re.DOTALL | re.IGNORECASE)
    
    for row in rows:
        cells = re.findall(r'<(td|th)[^>]*>(.*?)</\1>', row, re.DOTALL | re.IGNORECASE)
        if not cells:
            continue
            
        clean_cells = [re.sub(r'<[^>]+>', '', c[1]).strip() for c in cells]
        
        state_code = None
        for code, name in ALL_SENATE_RACES_2026.items():
            if len(clean_cells) > 0 and name.lower() in clean_cells[0].lower():
                state_code = code
                break
                
        if state_code:
            status = "tossup"
            note = "En attente des résultats"
            winner = ""
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

            results[state_code] = {"status": status, "note": note}
            if winner:
                results[state_code]["winner"] = winner

    return results

def main():
    print("Connexion à l'API Wikipedia pour les 35 scrutins sénatoriaux...")
    html = fetch_wiki_html("2026_United_States_Senate_elections")
    parsed_results = parse_results(html)
    
    output_results = {}
    for code in ALL_SENATE_RACES_2026.keys():
        if code in parsed_results:
            output_results[code] = parsed_results[code]
        else:
            output_results[code] = {"status": "tossup", "note": "En attente"}

    # 65 sièges ne sont pas remis en jeu (32 Démocrates/Indépendants alliés, 33 Républicains)
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "baseline_dem": 32,
        "baseline_rep": 33,
        "results": output_results
    }

    with open("results_senate.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Fichier results_senate.json mis à jour (35 États gérés) !")

if __name__ == "__main__":
    main()
