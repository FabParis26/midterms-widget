import json
import urllib.request
from datetime import datetime

DATA_URL = "https://projects.fivethirtyeight.com/polls/generic-ballot/538_generic_ballot_averages.json"

def fetch_polling_average():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    req = urllib.request.Request(DATA_URL, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            
        latest = raw_data[-1]
        dem_pct = round(latest.get('dem_estimate', 0), 1)
        rep_pct = round(latest.get('rep_estimate', 0), 1)
        margin = round(dem_pct - rep_pct, 1)
        
        output = {
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "democrats": dem_pct,
            "republicans": rep_pct,
            "margin": margin,
            "leading_party": "Démocrates" if margin > 0 else "Républicains"
        }
        
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print("Extraction réussie !")

    except Exception as e:
        print(f"Erreur de récupération : {e}")
        raise e

if __name__ == "__main__":
    fetch_polling_average()
