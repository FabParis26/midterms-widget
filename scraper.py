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
            date_str = row.get('date') or row.get('modeldate')
            candidate = (row.get('candidate') or row.get('party') or '').lower()
            pct_raw = row.get('pct_estimate') or row.get('pct_trend_adjusted')
            
            if not date_str or not pct_raw:
                continue
            try:
                pct = round(float(pct_raw), 1)
            except ValueError:
                continue

            if date_str not in by_date:
                by_date[date_str] = {}

            if candidate in ['democrats', 'dem', 'democrat']:
                by_date[date_str]['dem'] = pct
            elif candidate in ['republicans', 'rep', 'republican']:
                by_date[date_str]['rep'] = pct

        valid_dates = [d for d in by_date if 'dem' in by_date[d] and 'rep' in by_date[d]]
        valid_dates.sort()
        
        # 30 derniers jours
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
            
        print("Extraction et historique réussis !")

    except Exception as e:
        print(f"Erreur : {e}")
        raise e

if __name__ == "__main__":
    fetch_polling_average()
