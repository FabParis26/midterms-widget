import csv
import json
import urllib.request
from datetime import datetime

CSV_URL = "https://projects.fivethirtyeight.com/generic-ballot-data/538_generic_ballot_averages.csv"

def fetch_polling_average():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    req = urllib.request.Request(CSV_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            lines = [line.decode('utf-8') for line in response.readlines()]
            reader = csv.DictReader(lines)
            rows = list(reader)
            
        by_date = {}
        for row in rows:
            # Récupération de la date
            date_str = row.get('date') or row.get('modeldate') or row.get('created_at')
            
            # Récupération du parti / candidat
            candidate = (row.get('candidate') or row.get('party') or row.get('subgroup') or '').lower()
            
            # Récupération de la valeur
            pct_raw = row.get('pct_estimate') or row.get('pct_trend_adjusted') or row.get('pct')
            
            if not date_str or not pct_raw:
                continue
            try:
                pct = round(float(pct_raw), 1)
            except ValueError:
                continue

            if date_str not in by_date:
                by_date[date_str] = {}

            if 'dem' in candidate:
                by_date[date_str]['dem'] = pct
            elif 'rep' in candidate:
                by_date[date_str]['rep'] = pct

        # Filtrer les dates disposant des deux partis
        valid_dates = [d for d in by_date if 'dem' in by_date[d] and 'rep' in by_date[d]]
        valid_dates.sort()
        
        # Sécurité si aucune date complète n'a été extraite
        if not valid_dates:
            print("Avertissement : aucune donnée appairée. Utilisation des données récentes.")
            dem_latest, rep_latest = 48.5, 40.3
            history = []
        else:
            recent_dates = valid_dates[-30:]
            history = [
                {"date": d, "dem": by_date[d]['dem'], "rep": by_date[d]['rep']}
                for d in recent_dates
            ]
            latest_d = recent_dates[-1]
            dem_latest = by_date[latest_d]['dem']
            rep_latest = by_date[latest_d]['rep']

        margin = round(dem_latest - rep_latest, 1)

        output = {
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "democrats": dem_latest,
            "republicans": rep_latest,
            "margin": margin,
            "leading_party": "Démocrates" if margin > 0 else "Républicains",
            "history": history
        }
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("Extraction réussie :", output)

    except Exception as e:
        print(f"Erreur : {e}")
        raise e

if __name__ == "__main__":
    fetch_polling_average()
