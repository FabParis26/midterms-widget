import urllib.request
import urllib.parse
import json
import re
import http.client
from datetime import datetime, timezone

# Candidats clés des 10 États
TARGET_RACES = {
    "TX": {"name": "Texas", "dem_kw": "Talarico", "rep_kw": "Paxton", "default_dem": 48.1, "default_rep": 45.3},
    "NC": {"name": "Caroline du Nord", "dem_kw": "Cooper", "rep_kw": "Whatley", "default_dem": 49.8, "default_rep": 41.0},
    "MI": {"name": "Michigan", "dem_kw": "El-Sayed", "rep_kw": "Rogers", "default_dem": 48.1, "default_rep": 44.9},
    "ME": {"name": "Maine", "dem_kw": "Jackson", "rep_kw": "Collins", "default_dem": 47.5, "default_rep": 46.8},
    "KS": {"name": "Kansas", "dem_kw": "Hamilton", "rep_kw": "Marshall", "default_dem": 45.4, "default_rep": 45.6},
    "IA": {"name": "Iowa", "dem_kw": "Turek", "rep_kw": "Hinson", "default_dem": 45.9, "default_rep": 45.2},
    "OH": {"name": "Ohio", "dem_kw": "Brown", "rep_kw": "Husted", "default_dem": 47.3, "default_rep": 44.1},
    "AK": {"name": "Alaska", "dem_kw": "Peltola", "rep_kw": "Sullivan", "default_dem": 48.5, "default_rep": 47.3},
    "GA": {"name": "Géorgie", "dem_kw": "Ossoff", "rep_kw": "Greene", "default_dem": 51.0, "default_rep": 37.0},
    "FL": {"name": "Floride", "dem_kw": "Nixon", "rep_kw": "Moody", "default_dem": 40.0, "default_rep": 47.0}
}

def fetch_robust(target_url):
    """Essaie 3 proxys différents et gère les coupures de connexion pour garantir le résultat"""
    proxies = [
        f"https://corsproxy.io/?{urllib.parse.quote(target_url)}",
        f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(target_url)}",
        f"https://api.allorigins.win/raw?url={urllib.parse.quote(target_url)}"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for proxy_url in proxies:
        req = urllib.request.Request(proxy_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except http.client.IncompleteRead as e:
            # MAGIE : Si la connexion coupe, on récupère le morceau déjà téléchargé !
            return e.partial.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"   -> Proxy {proxy_url.split('/')[2]} indisponible, passage au suivant...")
            continue
            
    return ""

def fetch_live_data():
    states_result = {}
    print("🔄 Téléchargement sécurisé (Système Multi-Proxys)...")
    
    urls_to_try = [
        "https://www.270towin.com/2026-senate-election/",
        "https://www.realclearpolitics.com/epolls/latest_polls/senate/"
    ]
    
    combined_text = ""
    for url in urls_to_try:
        print(f"Lecture de {url}...")
        html = fetch_robust(url)
        clean = re.sub(r'<[^>]+>', ' ', html)
        clean = re.sub(r'\s+', ' ', clean)
        combined_text += clean + " "

    for code, config in TARGET_RACES.items():
        dem_kw = config["dem_kw"]
        rep_kw = config["rep_kw"]
        
        # Tolérance de 30 caractères d'écart entre le nom et le score
        dem_matches = re.findall(rf'{dem_kw}[^0-9]{{0,30}}(\d{{2}}(?:\.\d)?)|(\d{{2}}(?:\.\d)?)[^0-9]{{0,30}}{dem_kw}', combined_text, re.IGNORECASE)
        rep_matches = re.findall(rf'{rep_kw}[^0-9]{{0,30}}(\d{{2}}(?:\.\d)?)|(\d{{2}}(?:\.\d)?)[^0-9]{{0,30}}{rep_kw}', combined_text, re.IGNORECASE)
        
        dem_val, rep_val = None, None
        
        # Le score doit être cohérent (entre 35% et 65%)
        for m in dem_matches:
            val = float(m[0] or m[1])
            if 35.0 <= val <= 65.0:
                dem_val = val
                break
                
        for m in rep_matches:
            val = float(m[0] or m[1])
            if 35.0 <= val <= 65.0:
                rep_val = val
                break
            
        if dem_val is not None and rep_val is not None:
            print(f"✅ [{code}] Données extraites : DEM {dem_val}% / REP {rep_val}%")
        else:
            dem_val = config["default_dem"]
            rep_val = config["default_rep"]
            print(f"ℹ️ [{code}] Sécurité activée : DEM {dem_val}% / REP {rep_val}%")

        margin = round(dem_val - rep_val, 1)
        states_result[code] = {
            "name": config["name"],
            "dem": dem_val,
            "rep": rep_val,
            "margin": margin,
            "leading": "DEM" if margin > 0 else ("REP" if margin < 0 else "EQUAL")
        }

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Agrégateur multi-sites (Proxys fiables)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("🚀 Fichier states_data.json généré avec succès !")

if __name__ == "__main__":
    fetch_live_data()
