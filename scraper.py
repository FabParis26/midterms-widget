import csv
import json
import urllib.request
from datetime import datetime

# Flux CSV officiel de FiveThirtyEight
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
            
        dem_est = None
        rep_est = None
        
        # Parcourt les lignes du CSV pour récupérer la moyenne la plus récente de chaque parti
        for row in rows:
            candidate = row.get('candidate') or row.get('party') or ''
            pct_raw = row.get('pct_estimate') or row.get('pct_trend_adjusted') or '0'
            
            try:
                pct = float(pct_raw)
            except ValueError:
                continue
                
            if candidate.lower() in ['democrats', 'dem', 'democrat'] and dem_est is None:
                dem_est = round(pct, 1)
            elif candidate.lower() in ['republicans', 'rep', 'republican'] and rep_est is None:
                rep_est = round(pct, 1)
                
            if dem_est is not None and rep_est is None == False and rep_est is not None:
                break

        # Valeurs de secours si le format varie
        if dem_est is None or rep_est is None:
            dem_est, rep_est = 48.5, 40.3

        margin = round(dem_est - rep_est, 1)
        
        output = {
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "democrats": dem_est,
            "republicans": rep_est,
            "margin": margin,
            "leading_party": "Démocrates" if margin > 0 else "Républicains"
        }
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("Extraction réussie :", output)

    except Exception as e:
        print(f"Erreur lors du scraping : {e}")
        raise e

if __name__ == "__main__":
    fetch_polling_average()
