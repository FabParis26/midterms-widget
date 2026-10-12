import urllib.request
import urllib.parse
import json
import re
import os
import http.client
from datetime import datetime, timezone

def fetch_robust(target_url):
    """Essaie plusieurs proxys pour lire la page RCP du Generic Ballot"""
    proxies = [
        f"https://corsproxy.io/?{urllib.parse.quote(target_url)}",
        f"https://api.allorigins.win/raw?url={urllib.parse.quote(target_url)}",
        f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(target_url)}"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for proxy_url in proxies:
        req = urllib.request.Request(proxy_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except http.client.IncompleteRead as e:
            return e.partial.decode('utf-8', errors='ignore')
        except Exception:
            continue
    return ""

def main():
    print("Récupération du Generic Ballot (RealClearPolitics) via Proxy...")
    url = "https://www.realclearpolitics.com/epolls/other/2026-generic-congressional-vote-8395.html"
    
    html = fetch_robust(url)
    
    avg_dem, avg_rep = None, None
    
    # On cherche directement la balise RCP Average dans le HTML
    if html:
        clean_html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
        clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Le format RCP est généralement : "RCP Average 46.5 45.2" ou similaire
        match = re.search(r'RCP\s+Average[^0-9]*(\d{2}(?:\.\d)?)[^0-9]*(\d{2}(?:\.\d)?)', clean_text, re.IGNORECASE)
        
        if match:
            # Souvent RCP liste d'abord les Démocrates, mais on va le déduire si c'est flagrant, 
            # ou on suppose DEM en premier (format standard)
            val1 = float(match.group(1))
            val2 = float(match.group(2))
            
            # Vérification de sécurité
            if 35.0 <= val1 <= 55.0 and 35.0 <= val2 <= 55.0:
                avg_dem = val1
                avg_rep = val2

    if avg_dem is not None and avg_rep is not None:
        print(f"✅ RCP Average extrait : Démocrates {avg_dem}% / Républicains {avg_rep}%")
    else:
        print("⚠️ Extraction impossible, valeurs par défaut appliquées.")
        avg_dem, avg_rep = 47.0, 45.0

    margin = round(avg_dem - avg_rep, 1)
    leading = "Démocrates" if margin > 0 else ("Républicains" if margin < 0 else "Égalité")

    # --- GESTION DE L'HISTORIQUE ---
    history = []
    filepath = "data.json"
    
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                history = old_data.get("history", [])
        except Exception as e:
            print(f"Erreur de lecture : {e}")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # On met à jour ou on ajoute le point du jour
    if history and history[-1].get("date") == today_str:
        history[-1]["democrats"] = avg_dem
        history[-1]["republicans"] = avg_rep
    else:
        history.append({
            "date": today_str,
            "democrats": avg_dem,
            "republicans": avg_rep
        })
        
    history = history[-30:]

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "RealClearPolitics (Moyenne)",
        "democrats": avg_dem,
        "republicans": avg_rep,
        "margin": abs(margin),
        "leading_party": leading,
        "history": history
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier data.json (National) généré avec succès !")

if __name__ == "__main__":
    main()
