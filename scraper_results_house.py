import json
import re
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone

HEADERS = {'User-Agent': 'MidtermsWidget/1.0 (https://github.com/fabparis26/midterms-widget)'}
FILEPATH = "results_house.json"

def load_previous():
    if os.path.exists(FILEPATH):
        try:
            with open(FILEPATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def fetch_wiki_html():
    page = "2026_United_States_House_of_Representatives_elections"
    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page)}&format=json&prop=text"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('parse', {}).get('text', {}).get('*', '')
    except Exception as e:
        print(f"Erreur API Wikipedia : {e}")
    return ""

def parse_house_results(html):
    dem_seats = None
    rep_seats = None
    flips = []

    # Recherche dans l'infobox des totaux de sièges
    match_dem = re.search(r'Democratic(?:\s*\(.*?\))?.*?</td>\s*<td[^>]*>(\d{1,3})', html, re.DOTALL | re.IGNORECASE)
    match_rep = re.search(r'Republican(?:\s*\(.*?\))?.*?</td>\s*<td[^>]*>(\d{1,3})', html, re.DOTALL | re.IGNORECASE)

    if match_dem and match_rep:
        d = int(match_dem.group(1))
        r = int(match_rep.group(1))
        if 0 <= d <= 435 and 0 <= r <= 435 and (d + r) <= 435:
            dem_seats = d
            rep_seats = r

    # Extraction des bascules (Democratic gain / Republican gain)
    flip_matches = re.findall(r'([A-Z]{2}-\d{1,2}|[A-Za-z\s]+(?:\s+at-large|\s+\d{1,2}))\s*</td>.*?((?:Democratic|Republican)\s+gain)', html, re.DOTALL | re.IGNORECASE)
    for dist, kind in flip_matches[:10]:
        clean_dist = re.sub(r'<[^>]+>', '', dist).strip()
        to_party = "DEM" if "democratic" in kind.lower() else "REP"
        from_party = "REP" if to_party == "DEM" else "DEM"
        flips.append({
            "district": clean_dist,
            "state": clean_dist[:2] if len(clean_dist) >= 2 else "",
            "from": from_party,
            "to": to_party
        })

    return dem_seats, rep_seats, flips

def main():
    print("Connexion à l'API Wikipedia pour la Chambre des représentants...")
    html = fetch_wiki_html()
    prev = load_previous() or {}

    dem_seats, rep_seats, flips = parse_house_results(html)

    # Sécurité : conservation des données précédentes en cas d'absence
    if dem_seats is None or rep_seats is None:
        dem_seats = prev.get("dem_total", 0)
        rep_seats = prev.get("rep_total", 0)
        flips = prev.get("flips", [])
        print("Résultats en direct non encore disponibles sur Wikipédia -> maintien de l'état actuel.")
    else:
        print(f"Extraction réussie : DEM {dem_seats} / REP {rep_seats}")

    uncalled = max(0, 435 - dem_seats - rep_seats)

    # Calcul des gains nets par rapport à la composition de départ de la législature
    # En 2024-2026 : base approximative de 220 R / 213 D (ajustée selon les démissions)
    base_dem = 213
    base_rep = 220
    dem_gain = dem_seats - base_dem if dem_seats > 0 else 0
    rep_gain = rep_seats - base_rep if rep_seats > 0 else 0

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "dem_total": dem_seats,
        "rep_total": rep_seats,
        "uncalled": uncalled,
        "dem_gain": dem_gain,
        "rep_gain": rep_gain,
        "flips": flips
    }

    with open(FILEPATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Fichier {FILEPATH} mis à jour.")

if __name__ == "__main__":
    main()
