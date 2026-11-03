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

    # 1. Ciblage strict de la ligne des résultats validés ("Seats won" ou "Seats after")
    # Cela ignore formellement "Seats before" (qui contient 215 / 215)
    row_match = re.search(
        r'<tr[^>]*>\s*<th[^>]*>[^<]*Seats\s+(?:won|after)[^<]*</th>(.*?)(?:</tr>|$)',
        html,
        re.DOTALL | re.IGNORECASE
    )

    if row_match:
        cells = re.findall(r'<td[^>]*>(?:<[^>]+>)*\s*(\d{1,3})\s*(?:<[^>]+>)*</td>', row_match.group(1), re.DOTALL | re.IGNORECASE)
        if len(cells) < 2:
            cells = re.findall(r'<td[^>]*>.*?(\d{1,3}).*?</td>', row_match.group(1), re.DOTALL | re.IGNORECASE)

        if len(cells) >= 2:
            val1 = int(cells[0])
            val2 = int(cells[1])

            # Détection de l'ordre des colonnes dans l'infobox (GOP en col 1 car majorité sortante)
            rep_first = True
            party_row = re.search(r'<tr[^>]*>\s*<th[^>]*>[^<]*Party[^<]*</th>(.*?)(?:</tr>|$)', html, re.DOTALL | re.IGNORECASE)
            if party_row:
                p_cells = re.findall(r'<td[^>]*>(.*?)</td>', party_row.group(1), re.DOTALL | re.IGNORECASE)
                if len(p_cells) >= 2:
                    if 'democrat' in p_cells[0].lower():
                        rep_first = False
                    elif 'republican' in p_cells[0].lower():
                        rep_first = True

            rep = val1 if rep_first else val2
            dem = val2 if rep_first else val1

            if 0 <= dem <= 435 and 0 <= rep <= 435 and (dem + rep) <= 435:
                dem_seats = dem
                rep_seats = rep

    # 2. Extraction des bascules de circonscriptions (Flips)
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

    # Sécurité native : tant qu'aucun siège n'est proclamé dans "Seats won", on conserve l'état d'attente
    if dem_seats is None or rep_seats is None:
        dem_seats = prev.get("dem_total", 0)
        rep_seats = prev.get("rep_total", 0)
        flips = prev.get("flips", [])
        print("Résultats en direct non encore disponibles sur Wikipédia -> maintien de l'état actuel.")
    else:
        print(f"Extraction réussie : DEM {dem_seats} / REP {rep_seats}")

    uncalled = max(0, 435 - dem_seats - rep_seats)

    base_dem = 213
    base_rep = 220
    dem_gain = dem_seats - base_dem if dem_seats > 0 else 0
    rep_gain = rep_seats - base_rep if rep_seats > 0 else 0

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if (dem_seats > 0 or rep_seats > 0) else "En attente du dépouillement",
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
