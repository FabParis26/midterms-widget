from datetime import datetime, timezone
import json
import os
import re
import urllib.parse
import urllib.request

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
    "WY": "Wyoming",
}

HEADERS = {
    "User-Agent": (
        "MidtermsWidget/1.0 (https://github.com/fabparis26/midterms-widget)"
    )
}
FILEPATH = "results_senate.json"

# Textes génériques par défaut (à ne pas considérer comme des notes manuelles)
GENERIC_NOTES = {
    "en attente",
    "en attente des résultats",
    "scrutin très serré",
    "",
}


def load_previous():
  """Charge le fichier JSON existant pour préserver les interventions manuelles."""
  if os.path.exists(FILEPATH):
    try:
      with open(FILEPATH, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception as e:
      print(f"Notice: impossible de charger {FILEPATH} ({e})")
  return None


def fetch_wiki_html(page_title):
  api_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page_title)}&format=json&prop=text"
  req = urllib.request.Request(api_url, headers=HEADERS)
  try:
    with urllib.request.urlopen(req, timeout=12) as resp:
      data = json.loads(resp.read().decode("utf-8"))
      if "parse" in data and "text" in data["parse"]:
        return data["parse"]["text"]["*"]
  except Exception as e:
    print(f"Erreur API Wikipedia : {e}")
  return ""


def parse_results(html_content):
  results = {}
  tables = re.findall(
      r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
      html_content,
      re.DOTALL | re.IGNORECASE,
  )

  for table in tables:
    # 1. On élimine formellement les tableaux de prédictions, sondages et retraites
    table_lower = table.lower()
    if any(
        bad in table_lower
        for bad in [
            "ratings",
            "cook",
            "sabato",
            "ddhq",
            "predictions",
            "generic congressional ballot",
        ]
    ):
      continue

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL | re.IGNORECASE)
    for row in rows:
      cells = re.findall(
          r"<(td|th)[^>]*>(.*?)</\1>", row, re.DOTALL | re.IGNORECASE
      )
      if not cells:
        continue

      clean_cells = [re.sub(r"<[^>]+>", "", c[1]).strip() for c in cells]

      state_code = None
      for code, name in ALL_SENATE_RACES_2026.items():
        if len(clean_cells) > 0 and name.lower() in clean_cells[0].lower():
          state_code = code
          break

      if state_code:
        result_cell = clean_cells[-1].lower() if clean_cells else ""
        row_text = " ".join(clean_cells).lower()

        status = None
        winner = ""
        note = ""

        # Détection des victoires Démocrates (Holds, Gains ou Réélection)
        if any(
            p in result_cell
            for p in [
                "democratic hold",
                "democratic gain",
                "democrat hold",
                "democrat gain",
            ]
        ) or any(
            p in row_text
            for p in [
                "democratic hold",
                "democratic gain",
                "democrat hold",
                "democrat gain",
            ]
        ):
          status = "called_dem"
          winner = "Démocrate déclaré"
          note = "Victoire Démocrate (Wikipédia)"
        elif "re-elected" in result_cell and any(
            "democrat" in c.lower() for c in clean_cells[:3]
        ):
          status = "called_dem"
          winner = "Démocrate réélu"
          note = "Victoire Démocrate (Wikipédia)"

        # Détection des victoires Républicaines (Holds, Gains ou Réélection)
        elif any(
            p in result_cell
            for p in [
                "republican hold",
                "republican gain",
                "gop hold",
                "gop gain",
            ]
        ) or any(
            p in row_text
            for p in [
                "republican hold",
                "republican gain",
                "gop hold",
                "gop gain",
            ]
        ):
          status = "called_rep"
          winner = "Républicain déclaré"
          note = "Victoire Républicaine (Wikipédia)"
        elif "re-elected" in result_cell and any(
            "republican" in c.lower() for c in clean_cells[:3]
        ):
          status = "called_rep"
          winner = "Républicain réélu"
          note = "Victoire Républicaine (Wikipédia)"

        elif "too close to call" in row_text or "tossup" in row_text:
          status = "tossup"
          note = "Scrutin très serré"

        if status:
          # Si un État a déjà été validé victorieux, on ne le rétrograde pas en tossup
          if state_code in results and results[state_code].get("status") in [
              "called_dem",
              "called_rep",
          ]:
            continue
          results[state_code] = {"status": status, "note": note}
          if winner:
            results[state_code]["winner"] = winner

  return results


def main():
  print("Connexion à l'API Wikipedia pour les 35 scrutins sénatoriaux...")
  html = fetch_wiki_html("2026_United_States_Senate_elections")
  parsed_results = parse_results(html)

  # 1. Récupération des données précédentes existantes
  prev_json = load_previous() or {}
  prev_results = prev_json.get("results", {})

  output_results = {}
  for code in ALL_SENATE_RACES_2026.keys():
    prev_state = prev_results.get(code, {})
    wiki_state = parsed_results.get(code, None)

    # Règle 1 : Si Wikipédia a déclaré un vainqueur officiel
    if wiki_state and wiki_state.get("status") in [
        "called_dem",
        "called_rep",
        "dem",
        "rep",
    ]:
      output_results[code] = wiki_state

    # Règle 2 : Si vous avez validé manuellement un vainqueur dans le JSON (priorité maintenue)
    elif prev_state.get("status") in ["called_dem", "called_rep", "dem", "rep"]:
      output_results[code] = prev_state

    # Règle 3 : Le scrutin est toujours indécis (tossup)
    else:
      status = "tossup"
      prev_note = prev_state.get("note", "").strip()

      # Si vous avez écrit une note personnalisée (ex: "Démocrates en tête..."), elle est conservée
      if prev_note and prev_note.lower() not in GENERIC_NOTES:
        note = prev_note
      elif wiki_state:
        note = wiki_state.get("note", "En attente des résultats")
      else:
        note = prev_state.get("note", "En attente des résultats")

      output_results[code] = {"status": status, "note": note}

  # 65 sièges hors scrutin (34 Démocrates/Indépendants alliés, 31 Républicains)
  output = {
      "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
      "baseline_dem": 34,
      "baseline_rep": 31,
      "results": output_results,
  }

  with open(FILEPATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

  print(
      f"Fichier {FILEPATH} mis à jour (les vrais tableaux de résultats sont pris"
      " en compte) !"
  )


if __name__ == "__main__":
  main()
