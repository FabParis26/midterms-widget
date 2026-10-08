import json
import urllib.request
from datetime import datetime

DATA_URL = "https://projects.fivethirtyeight.com/polls/generic-ballot/538_generic_ballot_averages.json"

def fetch_polling_average():
    req = urllib.request.Request(
        DATA_URL, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    
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

if __name__ == "__main__":
    fetch_polling_average()
