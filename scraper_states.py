import json
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

TARGET_RACES = {
    "TX": {
        "name": "Texas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-paxton",
            "https://www.realclearpolling.com/polls/senate/general/2026/texas/talarico-vs-cornyn"
        ],
        "default_dem": 48.1, "default_rep": 45.3
    },
    "NC": {
        "name": "Caroline du Nord",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/north-carolina/cooper-vs-whatley"
        ],
        "default_dem": 49.8, "default_rep": 41.0
    },
    "MI": {
        "name": "Michigan",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/michigan/rogers-vs-el-sayed"
        ],
        "default_dem": 48.1, "default_rep": 44.9
    },
    "ME": {
        "name": "Maine",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/maine/collins-vs-platner"
        ],
        "default_dem": 47.5, "default_rep": 46.8
    },
    "KS": {
        "name": "Kansas",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/kansas/marshall-vs-hamilton"
        ],
        "default_dem": 45.4, "default_rep": 45.6
    },
    "IA": {
        "name": "Iowa",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/iowa/turek-vs-hinson"
        ],
        "default_dem": 45.9, "default_rep": 45.2
    },
    "OH": {
        "name": "Ohio",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/ohio/brown-vs-husted"
        ],
        "default_dem": 47.3, "default_rep": 44.1
    },
    "AK": {
        "name": "Alaska",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/alaska/peltola-vs-sullivan"
        ],
        "default_dem": 48.5, "default_rep": 47.3
    },
    "GA": {
        "name": "Géorgie",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/georgia/ossoff-vs-taylor-greene"
        ],
        "default_dem": 51.0, "default_rep": 37.0
    },
    "FL": {
        "name": "Floride",
        "urls": [
            "https://www.realclearpolling.com/polls/senate/general/2026/florida/nixon-vs-moody"
        ],
        "default_dem": 40.0, "default_rep": 50.0
    }
}

def scrape_race_with_playwright(page, urls):
    for url in urls:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            # Pause explicite pour laisser React exécuter le rendu dynamique du tableau
            page.wait_for_timeout(3500)

            content = page.content()
            clean_text = re.sub(r'<[^>]+>', ' ', content)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            d_pos = re.search(r'\([D|Democrat]\)', clean_text, re.I)
            r_pos = re.search(r'\([R|Republican|GOP]\)', clean_text, re.I)
            dem_first = True
            if d_pos and r_pos:
                dem_first = (d_pos.start() < r_pos.start())

            idx = clean_text.lower().find("rcp average")
            if idx != -1:
                snippet = clean_text[idx:idx+350]
                snippet = re.sub(r'\d{1,2}/\d{1,2}(?:\s*-\s*\d{1,2}/\d{1,2})?', ' ', snippet)
                snippet = re.sub(r'[—\-\|,]', ' ', snippet)

                nums = [float(x) for x in re.findall(r'\b(\d{2}(?:\.\d)?)\b', snippet) if 20.0 <= float(x) <= 80.0]

                if len(nums) >= 2:
                    dem_score = nums[0] if dem_first else nums[1]
                    rep_score = nums[1] if dem_first else nums[0]
                    print(f" SUCCESS [{url}] : DEM {dem_score}% / REP {rep_score}%")
                    return dem_score, rep_score
        except Exception as e:
            print(f" Playwright exception sur {url} : {e}")

    return None, None

def fetch_live_data():
    states_result = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for code, config in TARGET_RACES.items():
            dem_val, rep_val = scrape_race_with_playwright(page, config["urls"])

            if dem_val is None or rep_val is None:
                dem_val = config["default_dem"]
                rep_val = config["default_rep"]
                print(f" Fallback appliqué pour [{code}]")

            margin = round(dem_val - rep_val, 1)
            states_result[code] = {
                "name": config["name"],
                "dem": dem_val,
                "rep": rep_val,
                "margin": margin,
                "leading": "DEM" if margin > 0 else ("REP" if margin < 0 else "EQUAL")
            }

        browser.close()

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "RealClearPolling (En direct - Playwright)",
        "states": states_result
    }

    with open("states_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(" Extraction terminée et enregistrée !")

if __name__ == "__main__":
    fetch_live_data()
