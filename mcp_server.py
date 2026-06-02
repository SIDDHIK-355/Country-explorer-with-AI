"""
Travel Guide MCP Server
Tools: get_country_info, get_top_places, get_local_food, save_to_wishlist, build_travel_page
"""

import json
import sys
import webbrowser
from pathlib import Path

def _log(msg): print(f"      [MCP] {msg}", file=sys.stderr, flush=True)

import requests
from fastmcp import FastMCP

mcp = FastMCP("TravelServer")

WORLD_PLACES = [
    {"name": "Taj Mahal",            "country": "India",    "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Taj_Mahal_%28Edited%29.jpeg/960px-Taj_Mahal_%28Edited%29.jpeg"},
    {"name": "Machu Picchu",         "country": "Peru",     "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Peru_Machu_Picchu_Sunrise.jpg/960px-Peru_Machu_Picchu_Sunrise.jpg"},
    {"name": "Christ the Redeemer",  "country": "Brazil",   "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Christ_the_Redeemer_-_Cristo_Redentor.jpg/960px-Christ_the_Redeemer_-_Cristo_Redentor.jpg"},
    {"name": "Neuschwanstein Castle","country": "Germany",  "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Schloss_Neuschwanstein_2013.jpg/960px-Schloss_Neuschwanstein_2013.jpg"},
    {"name": "Colosseum",            "country": "Italy",    "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Colosseo_2020.jpg/960px-Colosseo_2020.jpg"},
    {"name": "Angkor Wat",           "country": "Cambodia", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Buddhist_monks_in_front_of_the_Angkor_Wat.jpg/960px-Buddhist_monks_in_front_of_the_Angkor_Wat.jpg"},
    {"name": "Santorini",            "country": "Greece",   "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bf/2011_Dimos_Thiras.png/960px-2011_Dimos_Thiras.png"},
    {"name": "Petra",                "country": "Jordan",   "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Al_Deir_Petra.JPG/960px-Al_Deir_Petra.JPG"},
    {"name": "Great Wall of China",  "country": "China",    "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/The_Great_Wall_of_China_at_Jinshanling-edit.jpg/960px-The_Great_Wall_of_China_at_Jinshanling-edit.jpg"},
    {"name": "Victoria Falls",       "country": "Zimbabwe", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Cataratas_Victoria%2C_Zambia-Zimbabue%2C_2018-07-27%2C_DD_04.jpg/960px-Cataratas_Victoria%2C_Zambia-Zimbabue%2C_2018-07-27%2C_DD_04.jpg"},
    {"name": "Sagrada Família",      "country": "Spain",    "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/SF_maig_2026.jpg/960px-SF_maig_2026.jpg"},
    {"name": "Acropolis of Athens",  "country": "Greece",   "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/1029_Acropolis_of_Athens_in_Greece_at_night_Photo_by_Giles_Laurent.jpg/960px-1029_Acropolis_of_Athens_in_Greece_at_night_Photo_by_Giles_Laurent.jpg"},
]

HERE = Path(__file__).parent
DATA_FILE = HERE / "data" / "countries.json"
DATA_FILE.parent.mkdir(exist_ok=True)
if not DATA_FILE.exists():
    DATA_FILE.write_text("{}", encoding="utf-8")

HTML_OUT = HERE / "travel_guide.html"


@mcp.tool()
def get_country_info(country_name: str) -> str:
    """Fetch country details: flag, capital, population, region, languages, currency, coordinates."""
    _log(f"GET restcountries.com/v3.1/name/{country_name}")
    resp = requests.get(
        f"https://restcountries.com/v3.1/name/{country_name}", timeout=10
    )
    resp.raise_for_status()
    d = resp.json()[0]
    _log(f"Received: {d['name']['common']} ({d.get('region','')})")
    return json.dumps({
        "name": d["name"]["common"],
        "official": d["name"]["official"],
        "flag_emoji": d.get("flag", ""),
        "flag_url": d.get("flags", {}).get("png", ""),
        "capital": (d.get("capital") or [""])[0],
        "population": d.get("population", 0),
        "area_km2": d.get("area", 0),
        "region": d.get("region", ""),
        "subregion": d.get("subregion", ""),
        "languages": list(d.get("languages", {}).values()),
        "currencies": [
            f"{v['name']} ({v.get('symbol', '')})"
            for v in d.get("currencies", {}).values()
        ],
        "currency_codes": list(d.get("currencies", {}).keys()),
        "timezones": d.get("timezones", []),
        "latlng": d.get("latlng", [0, 0]),
    })


_BAD_IMG_KEYWORDS = ("flag_of", "flag_of_", "coat_of_arms", "logo", "seal_of",
                     "emblem", "icon", "symbol", "wikimedia", "commons-logo")

def _is_good_photo(url: str) -> bool:
    """Return False for flags, logos, and other non-photo images."""
    low = url.lower()
    return not any(kw in low for kw in _BAD_IMG_KEYWORDS)


def _wiki_image(title: str, size: int = 500) -> str:
    """Fetch the main thumbnail image URL for a Wikipedia article."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": size,
        }
        headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=8)
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            src = page.get("thumbnail", {}).get("source", "")
            if src:
                return src
    except Exception:
        pass
    return ""


def _wiki_images_batch(wiki_titles: list[str], size: int = 600) -> dict[str, str]:
    """Fetch thumbnails for multiple Wikipedia articles in one API call."""
    try:
        params = {
            "action": "query",
            "titles": "|".join(wiki_titles),
            "prop": "pageimages",
            "format": "json",
            "pithumbsize": size,
        }
        headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=15)
        pages = resp.json().get("query", {}).get("pages", {})
        result = {}
        for page in pages.values():
            title = page.get("title", "")
            img = page.get("thumbnail", {}).get("source", "")
            if title and img:
                result[title] = img
        return result
    except Exception:
        return {}


def _wiki_images_for_country(country_name: str) -> list[str]:
    """Fetch up to 10 photos for a country via Wikipedia searches."""
    queries = [
        f"{country_name} landscape",
        f"{country_name} city skyline",
        f"{country_name} culture",
        f"Tourism in {country_name}",
        f"{country_name} nature",
        f"{country_name} architecture",
        f"{country_name} mountains",
        f"{country_name} coast beach",
        f"{country_name} historical site",
        f"{country_name} national park",
    ]
    images = []
    headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
    for q in queries:
        if len(images) >= 10:
            break
        try:
            search_params = {"action": "query", "list": "search", "srsearch": q, "srlimit": 2, "format": "json"}
            r = requests.get("https://en.wikipedia.org/w/api.php", params=search_params, headers=headers, timeout=8)
            for item in r.json().get("query", {}).get("search", []):
                title = item.get("title", "")
                if title:
                    img = _wiki_image(title, size=800)
                    if img and img not in images and _is_good_photo(img):
                        images.append(img)
                        break
        except Exception:
            pass
    return images


def _wiki_extract(title: str) -> str:
    """Get the first sentence of a Wikipedia article as a description."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exsentences": 2,
            "exintro": True,
            "explaintext": True,
            "format": "json",
        }
        headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=8)
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            text = page.get("extract", "").strip()
            if text:
                return text[:180]
    except Exception:
        pass
    return ""


@mcp.tool()
def get_top_places(place_names_json: str) -> str:
    """Fetch Wikipedia photo and description for each place — uses batch requests to avoid rate limiting."""
    try:
        place_names = json.loads(place_names_json)
        headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}

        _log(f"Batch image fetch: en.wikipedia.org ({len(place_names)} titles)")
        # Batch fetch images (one request for all places)
        img_resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": "|".join(place_names),
                    "prop": "pageimages", "format": "json", "pithumbsize": 600},
            headers=headers, timeout=20,
        )
        img_data = img_resp.json().get("query", {})
        img_normalized = {n["from"]: n["to"] for n in img_data.get("normalized", [])}
        images = {p.get("title", ""): p.get("thumbnail", {}).get("source", "")
                  for p in img_data.get("pages", {}).values()}

        _log(f"Batch description fetch: en.wikipedia.org ({len(place_names)} titles)")
        # Batch fetch descriptions (one request for all places)
        ext_resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "titles": "|".join(place_names),
                    "prop": "extracts", "exsentences": 2, "exintro": True,
                    "explaintext": True, "format": "json"},
            headers=headers, timeout=20,
        )
        ext_data = ext_resp.json().get("query", {})
        ext_normalized = {n["from"]: n["to"] for n in ext_data.get("normalized", [])}
        extracts = {p.get("title", ""): p.get("extract", "").strip()[:180]
                    for p in ext_data.get("pages", {}).values()}

        places = []
        for name in place_names:
            img_title = img_normalized.get(name, name)
            ext_title = ext_normalized.get(name, name)
            places.append({
                "name": name,
                "description": extracts.get(ext_title, ""),
                "photo": images.get(img_title, ""),
            })
        return json.dumps(places)
    except Exception as e:
        return json.dumps([{"name": "Unknown", "description": str(e), "photo": ""}])


_CUISINE_DISHES: dict[str, list[str]] = {
    "Indian":     ["Biryani", "Butter chicken", "Rogan josh", "Palak paneer", "Masala dosa", "Samosa",
                   "Tandoori chicken", "Gulab jamun", "Dal makhani", "Chana masala", "Naan",
                   "Chicken tikka masala", "Pani puri", "Aloo paratha", "Kheer", "Chole bhature",
                   "Idli", "Vada pav", "Pav bhaji", "Rasgulla"],
    "Pakistani":  ["Nihari", "Biryani", "Haleem", "Karahi", "Chapli kabab", "Seekh kebab",
                   "Paya soup", "Sheer khurma", "Mutton korma", "Daal chawal",
                   "Saag", "Lassi", "Bun kebab", "Dum pukht"],
    "Sri Lankan": ["Hoppers", "Kottu roti", "Rice and curry", "Fish ambul thiyal", "Wambatu moju",
                   "Pol sambol", "String hoppers", "Lamprais", "Kiribath", "Crab curry",
                   "Pittu", "Wattalapam", "Isso wade"],
    "Bangladeshi":["Hilsa curry", "Biryani", "Panta bhat", "Shorshe ilish", "Kacchi biryani",
                   "Mishti doi", "Bhuna khichuri", "Patishapta", "Chingri malai curry", "Halwa"],
    "Ethiopian":  ["Injera", "Doro wat", "Kitfo", "Tibs", "Shiro", "Teff",
                   "Misir wat", "Gored gored", "Ayib", "Tej", "Firfir", "Kategna"],
    "Nigerian":   ["Jollof rice", "Egusi soup", "Suya", "Puff-puff", "Banga soup", "Akara",
                   "Moi moi", "Pepper soup", "Eba", "Okra soup", "Tuwo shinkafa", "Chin chin"],
    "Peruvian":   ["Ceviche", "Lomo saltado", "Aji de gallina", "Causa limeña", "Anticuchos",
                   "Picarones", "Arroz con leche", "Papa a la huancaína", "Tacu tacu", "Leche de tigre",
                   "Seco de res", "Rocoto relleno"],
    "Brazilian":  ["Feijoada", "Pão de queijo", "Brigadeiro", "Moqueca", "Açaí",
                   "Coxinha", "Picanha", "Acarajé", "Beijinho", "Quindim",
                   "Churrasco", "Pastel", "Tapioca"],
    "Argentine":  ["Asado", "Empanada", "Chimichurri", "Dulce de leche", "Medialunas", "Locro",
                   "Milanesa", "Choripán", "Alfajor", "Provoleta", "Humita", "Mate"],
    "Korean":     ["Kimchi", "Bibimbap", "Bulgogi", "Tteokbokki", "Japchae", "Samgyeopsal",
                   "Doenjang jjigae", "Sundubu jjigae", "Naengmyeon", "Haemul pajeon",
                   "Galbi", "Bingsu", "Dakgalbi"],
    "Vietnamese": ["Pho", "Banh mi", "Goi cuon", "Bun bo Hue", "Com tam", "Banh xeo",
                   "Bun cha", "Cao lau", "Mi quang", "Chao ga", "Banh cuon", "Cha ca"],
    "Afghan":     ["Kabuli pulao", "Mantu", "Bolani", "Ashak", "Qorma", "Shorwa",
                   "Sheer yakh", "Firni", "Boulanee", "Sholeh zard"],
    "Iranian":    ["Ghormeh sabzi", "Fesenjan", "Kebab koobideh", "Tahdig", "Ash reshteh",
                   "Mirza ghasemi", "Khoresh bademjan", "Zereshk polo", "Halva", "Baklava"],
    "Turkish":    ["Doner kebab", "Baklava", "Manti", "Lahmacun", "Pide",
                   "Iskender kebab", "Menemen", "Simit", "Gozleme", "Sutlac"],
    "Lebanese":   ["Hummus", "Falafel", "Tabbouleh", "Kibbeh", "Fattoush",
                   "Shawarma", "Manakish", "Kafta", "Warak dawali", "Baklava"],
}


def _wiki_food_fallback(cuisine: str) -> list[dict]:
    """Batch-fetch Wikipedia dish images+descriptions for cuisines TheMealDB doesn't cover."""
    dishes = _CUISINE_DISHES.get(cuisine, [f"{cuisine} cuisine", f"Traditional {cuisine} food",
                                            f"{cuisine} dishes", f"{cuisine} street food",
                                            f"{cuisine} dessert", f"{cuisine} bread"])
    try:
        headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
        params = {"action": "query", "titles": "|".join(dishes),
                  "prop": "pageimages|extracts", "format": "json", "pithumbsize": 600,
                  "exsentences": 2, "exintro": True, "explaintext": True, "redirects": True}
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=15)
        data = resp.json().get("query", {})
        normalized = {n["from"]: n["to"] for n in data.get("normalized", [])}
        pages = data.get("pages", {})
        img_map = {p.get("title", ""): p.get("thumbnail", {}).get("source", "") for p in pages.values()}
        desc_map = {p.get("title", ""): p.get("extract", "").strip()[:200] for p in pages.values()}
        food = []
        for dish in dishes:
            actual = normalized.get(dish, dish)
            img = img_map.get(actual, "")
            if img:
                food.append({"name": dish, "photo": img, "description": desc_map.get(actual, "")})
        return food[:20]
    except Exception:
        return []


@mcp.tool()
def get_local_food(cuisine: str) -> str:
    """Get famous dishes with photos and descriptions from TheMealDB, with Wikipedia fallback."""
    _log(f"GET themealdb.com/filter.php?a={cuisine}")
    resp = requests.get(
        f"https://www.themealdb.com/api/json/v1/1/filter.php?a={cuisine}", timeout=10
    )
    meals = resp.json().get("meals") or []
    _log(f"TheMealDB returned {len(meals)} meals")
    food = [
        {"name": m["strMeal"], "photo": m["strMealThumb"] + "/preview"}
        for m in meals[:20]
    ]
    if not food:
        food = _wiki_food_fallback(cuisine)
    else:
        # Batch-fetch Wikipedia descriptions for TheMealDB dishes
        try:
            names = [f["name"] for f in food[:20]]
            _log(f"Batch description fetch: en.wikipedia.org ({len(names)} dish titles)")
            headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
            # Pass 1: exact title batch lookup
            params = {"action": "query", "titles": "|".join(names),
                      "prop": "extracts", "exsentences": 2, "exintro": True,
                      "explaintext": True, "redirects": True, "format": "json"}
            r = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=10)
            qdata = r.json().get("query", {})
            norm = {n["from"]: n["to"] for n in qdata.get("normalized", [])}
            redir = {n["from"]: n["to"] for n in qdata.get("redirects", [])}
            desc_map = {p.get("title", ""): p.get("extract", "").strip()[:200]
                        for p in qdata.get("pages", {}).values()}
            for item in food:
                t1 = norm.get(item["name"], item["name"])
                t2 = redir.get(t1, t1)
                item["description"] = desc_map.get(t2, desc_map.get(t1, ""))
            # Pass 2: search-based lookup for dishes still missing descriptions
            missing = [item for item in food if not item.get("description")]
            if missing:
                search_map = {}
                for item in missing:
                    try:
                        sr = requests.get("https://en.wikipedia.org/w/api.php", params={
                            "action": "query", "list": "search",
                            "srsearch": item["name"] + " food dish",
                            "srlimit": 1, "format": "json"
                        }, headers=headers, timeout=6)
                        hits = sr.json().get("query", {}).get("search", [])
                        if hits:
                            search_map[item["name"]] = hits[0]["title"]
                    except Exception:
                        pass
                if search_map:
                    er = requests.get("https://en.wikipedia.org/w/api.php", params={
                        "action": "query", "titles": "|".join(search_map.values()),
                        "prop": "extracts", "exsentences": 2, "exintro": True,
                        "explaintext": True, "format": "json"
                    }, headers=headers, timeout=10)
                    enorm = {n["from"]: n["to"] for n in er.json().get("query", {}).get("normalized", [])}
                    edesc = {p.get("title", ""): p.get("extract", "").strip()[:200]
                             for p in er.json().get("query", {}).get("pages", {}).values()}
                    for orig, wiki_t in search_map.items():
                        actual = enorm.get(wiki_t, wiki_t)
                        desc = edesc.get(actual, "")
                        if desc:
                            for item in food:
                                if item["name"] == orig:
                                    item["description"] = desc
            # Pass 3: default fallback so no card is ever blank
            for item in food:
                if not item.get("description"):
                    item["description"] = f"A traditional {cuisine} dish."
        except Exception:
            pass
    return json.dumps(food)


@mcp.tool()
def get_food_by_names(dish_names_json: str) -> str:
    """Fetch Wikipedia photos and descriptions for Groq-generated dish names (any country)."""
    try:
        dishes = json.loads(dish_names_json)
    except Exception:
        return "[]"
    if not dishes:
        return "[]"
    headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
    _log(f"Batch image+desc fetch: en.wikipedia.org ({len(dishes)} dish titles)")
    # Pass 1: batch fetch images + descriptions
    params = {
        "action": "query", "titles": "|".join(dishes[:20]),
        "prop": "pageimages|extracts", "format": "json", "pithumbsize": 600,
        "exsentences": 2, "exintro": True, "explaintext": True, "redirects": True,
    }
    try:
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=headers, timeout=15)
        qdata = resp.json().get("query", {})
        norm = {n["from"]: n["to"] for n in qdata.get("normalized", [])}
        redir = {n["from"]: n["to"] for n in qdata.get("redirects", [])}
        def _resolve(title):
            t1 = norm.get(title, title)
            return redir.get(t1, t1)
        img_map = {p.get("title", ""): p.get("thumbnail", {}).get("source", "") for p in qdata.get("pages", {}).values()}
        desc_map = {p.get("title", ""): p.get("extract", "").strip()[:200] for p in qdata.get("pages", {}).values()}
    except Exception:
        img_map, desc_map = {}, {}
        def _resolve(t): return t

    food = []
    missing_img = []
    for dish in dishes[:20]:
        actual = _resolve(dish)
        img = img_map.get(actual, "")
        desc = desc_map.get(actual, "")
        food.append({"name": dish, "photo": img, "description": desc})
        if not img:
            missing_img.append(dish)

    # Pass 2: search-based image lookup for dishes still missing photos
    if missing_img:
        _log(f"Search fallback for {len(missing_img)} dishes without photos")
        search_map = {}
        for dish in missing_img:
            try:
                sr = requests.get("https://en.wikipedia.org/w/api.php", params={
                    "action": "query", "list": "search",
                    "srsearch": dish + " food dish", "srlimit": 1, "format": "json"
                }, headers=headers, timeout=6)
                hits = sr.json().get("query", {}).get("search", [])
                if hits:
                    search_map[dish] = hits[0]["title"]
            except Exception:
                pass
        if search_map:
            try:
                er = requests.get("https://en.wikipedia.org/w/api.php", params={
                    "action": "query", "titles": "|".join(search_map.values()),
                    "prop": "pageimages|extracts", "format": "json", "pithumbsize": 600,
                    "exsentences": 2, "exintro": True, "explaintext": True,
                }, headers=headers, timeout=10)
                enorm = {n["from"]: n["to"] for n in er.json().get("query", {}).get("normalized", [])}
                epages = er.json().get("query", {}).get("pages", {})
                eimg = {p.get("title", ""): p.get("thumbnail", {}).get("source", "") for p in epages.values()}
                edesc = {p.get("title", ""): p.get("extract", "").strip()[:200] for p in epages.values()}
                for orig, wiki_t in search_map.items():
                    actual = enorm.get(wiki_t, wiki_t)
                    for item in food:
                        if item["name"] == orig:
                            if not item["photo"] and eimg.get(actual):
                                item["photo"] = eimg[actual]
                            if not item["description"] and edesc.get(actual):
                                item["description"] = edesc[actual]
            except Exception:
                pass

    # Pass 3: drop dishes that still have no photo, cap at 20
    food = [f for f in food if f.get("photo")][:20]

    # Pass 4: default description fallback so no card is blank
    for item in food:
        if not item.get("description"):
            item["description"] = f"A traditional dish."

    _log(f"get_food_by_names: returning {len(food)} dishes with photos")
    return json.dumps(food)


@mcp.tool()
def get_city_coords(country_name: str, cities_json: str) -> str:
    """Geocode top cities using the Open-Meteo geocoding API (free, no key needed)."""
    try:
        cities = json.loads(cities_json)
    except Exception:
        return "[]"
    result = []
    headers = {"User-Agent": "TravelGuideApp/1.0 (educational project)"}
    for city in cities[:15]:
        try:
            _log(f"Geocoding: {city}, {country_name}")
            r = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": f"{city}", "count": 3, "language": "en", "format": "json"},
                headers=headers, timeout=6,
            )
            hits = r.json().get("results", [])
            # Pick the hit that matches the country
            chosen = None
            for h in hits:
                if country_name.lower() in h.get("country", "").lower():
                    chosen = h
                    break
            if not chosen and hits:
                chosen = hits[0]
            if chosen:
                result.append({
                    "city": city,
                    "lat": round(chosen["latitude"], 4),
                    "lng": round(chosen["longitude"], 4),
                })
        except Exception:
            pass
    _log(f"Geocoded {len(result)}/{len(cities[:15])} cities")
    return json.dumps(result)


@mcp.tool()
def save_to_wishlist(country_name: str, info_json: str) -> str:
    """Save a country's info to the local travel wishlist JSON file."""
    wishlist = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    wishlist[country_name] = json.loads(info_json)
    DATA_FILE.write_text(json.dumps(wishlist, indent=2), encoding="utf-8")
    return f"Saved {country_name}. Wishlist now has {len(wishlist)} countries."


@mcp.tool()
def build_travel_page(country_info_json: str, places_json: str, food_json: str, description: str = "", weather_json: str = "[]") -> str:
    """Generate a beautiful HTML travel guide page and open it in the browser."""
    info = json.loads(country_info_json)
    places = json.loads(places_json)
    food = json.loads(food_json)
    weather_cities = json.loads(weather_json) if weather_json else []

    name = info["name"]
    lat, lng = info["latlng"][0], info["latlng"][1]
    pop = f"{info['population']:,}"
    currency = info["currencies"][0] if info["currencies"] else "N/A"
    lang = ", ".join(info["languages"][:2]) if info["languages"] else "N/A"
    currency_code = (info.get("currency_codes") or ["USD"])[0]
    currency_name_full = currency.split(" (")[0] if currency != "N/A" else "Local Currency"

    # World landmarks — images are hardcoded, no API call needed
    # Carousel — combine place photos (with names) + country-wide photos, up to 10
    place_photo_map = {p["photo"]: p["name"] for p in places if p.get("photo")}
    _log(f"Fetching country scenery photos: en.wikipedia.org ({name})")
    country_photos = _wiki_images_for_country(name)
    seen: set[str] = set()
    all_photo_items: list[dict] = []
    for img in list(place_photo_map.keys()) + country_photos:
        if img and img not in seen:
            seen.add(img)
            label = place_photo_map.get(img, name)
            all_photo_items.append({"img": img, "label": label})
        if len(all_photo_items) == 30:
            break
    if not all_photo_items:
        all_photo_items = [{"img": "", "label": name}]

    carousel_items = "\n".join(
        f'''<div class="carr-item">
  <img src="{item['img']}" alt="{item['label']}" loading="lazy">
  <div class="carr-label">{item['label']}</div>
</div>'''
        for item in all_photo_items
    )
    world_cards_list = [
        {"name": wp["name"], "country": wp["country"], "photo": wp["img"]}
        for wp in WORLD_PLACES
    ]

    place_cards = "\n".join(
        f"""<div class="card">
  {'<img src="' + w['photo'] + '" alt="' + w['name'] + '" loading="lazy">' if w.get('photo') else '<div class="card-no-img">🌍</div>'}
  <div class="card-body"><h3>{w['name']}</h3><p class="card-country">📍 {w['country']}</p></div>
</div>"""
        for w in world_cards_list
    )

    # Food list (horizontal cards)
    food_cards = (
        "\n".join(
            f"""<div class="food-item">
  <img src="{f['photo']}" alt="{f['name']}" loading="lazy">
  <div class="food-info">
    <h3>{f['name']}</h3>
    {f'<p>{f["description"]}</p>' if f.get("description") else ''}
  </div>
</div>"""
            for f in food
        )
        if food
        else '<p style="color:#94a3b8;padding:20px">No meal data found for this cuisine.</p>'
    )

    # Weather city cards (skeleton — JS fills in live data)
    weather_cards_html = (
        "\n".join(
            f"""<div class="wc-card">
  <div class="wc-left-panel">
    <span class="wc-emoji" id="wemoji-{i}">⏳</span>
    <div class="wc-temprow">
      <span class="wc-temp" id="wtemp-{i}">—</span>
      <span class="wc-unit">°C</span>
    </div>
  </div>
  <div class="wc-right-panel">
    <div class="wc-city">{c['city']}</div>
    <div class="wc-desc" id="wdesc-{i}">Loading...</div>
    <div class="wc-stats" id="wstats-{i}"></div>
    <div class="wc-chart-wrap"><canvas id="wchart-{i}"></canvas></div>
    <div class="wc-forecast" id="wforecast-{i}"></div>
  </div>
</div>"""
            for i, c in enumerate(weather_cities)
        )
        if weather_cities
        else '<p style="color:#94a3b8;padding:20px">No city weather data available.</p>'
    )
    weather_cities_js = json.dumps(weather_cities)

    # Zoom level based on country area
    area = info.get("area_km2", 0)
    if area > 5_000_000:
        map_zoom = 3
    elif area > 2_000_000:
        map_zoom = 4
    elif area > 300_000:
        map_zoom = 5
    elif area > 50_000:
        map_zoom = 6
    else:
        map_zoom = 7
    name_js = json.dumps(name)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Travel Guide</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0}}
/* Header */
.header{{padding:20px 40px;display:flex;align-items:center;gap:16px;background:#1e293b;border-bottom:1px solid #334155;justify-content:space-between}}
.header-left{{display:flex;align-items:center;gap:16px;flex:1}}
.flag{{font-size:52px;flex-shrink:0}}
.country-name h1{{font-size:2.2rem;font-weight:700}}
.country-name p{{color:#94a3b8;margin-top:4px;font-size:.95rem}}
.header-mid{{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;padding:0 32px;align-content:center}}
.mid-item{{display:flex;flex-direction:column;gap:2px}}
.mid-label{{font-size:.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em}}
.mid-value{{font-size:.82rem;color:#e2e8f0;font-weight:500;word-break:break-word}}
/* Carousel */
.carousel-wrap{{position:relative;padding:24px 64px;background:#0f172a}}
.carousel-viewport{{overflow:hidden;border-radius:14px}}
.carousel-track{{display:flex;gap:12px;transition:transform .45s ease}}
.carr-item{{flex:0 0 calc(33.333% - 8px);border-radius:14px;overflow:hidden;height:300px;position:relative}}
.carr-item img{{width:100%;height:100%;object-fit:cover;display:block}}
.carr-label{{position:absolute;bottom:0;left:0;right:0;padding:10px 14px;background:linear-gradient(transparent,rgba(0,0,0,.78));color:#fff;font-size:.85rem;font-weight:600;letter-spacing:.02em}}
.carr-btn{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(15,23,42,.75);border:2px solid #334155;color:#e2e8f0;font-size:20px;width:48px;height:48px;border-radius:50%;cursor:pointer;z-index:5;display:flex;align-items:center;justify-content:center;transition:background .2s}}
.carr-btn:hover{{background:#1e293b}}
.carr-prev{{left:10px}}.carr-next{{right:10px}}
/* Stats */
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#334155}}
.stat{{background:#1e293b;padding:18px;text-align:center}}
.stat .val{{font-size:1.1rem;font-weight:700;color:#60a5fa;word-break:break-word}}
.stat .lbl{{font-size:.78rem;color:#94a3b8;margin-top:4px}}
/* Tabs */
.tabs{{display:flex;background:#1e293b;border-bottom:1px solid #334155;padding:0 40px}}
.tab{{padding:14px 22px;cursor:pointer;color:#94a3b8;border-bottom:3px solid transparent;font-size:.9rem;transition:all .2s}}
.tab.active{{color:#60a5fa;border-bottom-color:#60a5fa}}
/* Content */
.content{{padding:28px 40px}}
.panel{{display:none}}.panel.active{{display:block}}
/* Places grid */
.grid-6{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}}
.card{{background:#1e293b;border-radius:14px;overflow:hidden;transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-5px);box-shadow:0 12px 32px rgba(0,0,0,.4)}}
.card img{{width:100%;height:130px;object-fit:cover}}
.card-no-img{{width:100%;height:130px;display:flex;align-items:center;justify-content:center;font-size:2rem;background:#334155}}
.card-body{{padding:8px 10px}}
.card-body h3{{font-size:.78rem;font-weight:600;margin-bottom:2px}}
.card-body p{{font-size:.78rem;color:#94a3b8;line-height:1.45}}
.card-country{{color:#60a5fa!important;font-size:.7rem;margin-top:2px}}
/* Food list */
.food-list{{display:flex;flex-direction:column;gap:10px}}
.food-item{{display:flex;align-items:stretch;background:#1e293b;border-radius:12px;overflow:hidden;transition:transform .2s,box-shadow .2s}}
.food-item:hover{{transform:translateX(5px);box-shadow:0 4px 20px rgba(0,0,0,.4)}}
.food-item img{{width:140px;height:100px;object-fit:cover;flex-shrink:0}}
.food-info{{padding:14px 18px;flex:1;display:flex;flex-direction:column;justify-content:center}}
.food-info h3{{font-size:.95rem;font-weight:600;color:#e2e8f0;margin-bottom:5px}}
.food-info p{{font-size:.8rem;color:#94a3b8;line-height:1.5;margin:0}}
/* Map panel */
.map-container{{border-radius:14px;overflow:hidden;height:650px;border:1px solid #334155}}
.leaflet-control-attribution{{font-size:.62rem!important;background:rgba(15,23,42,.85)!important;color:#94a3b8!important}}
.leaflet-control-attribution a{{color:#60a5fa!important}}
.leaflet-control-layers{{background:#1e293b!important;border:1px solid #334155!important;border-radius:8px!important;color:#e2e8f0!important}}
.leaflet-control-layers-selector{{accent-color:#60a5fa}}
.leaflet-bar a{{background:#1e293b!important;color:#e2e8f0!important;border-color:#334155!important}}
.leaflet-bar a:hover{{background:#334155!important}}
/* Currency Dashboard */
.currency-section{{background:#1e293b;border-top:1px solid #334155;padding:22px 40px}}
.currency-top{{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}}
.currency-left{{flex-shrink:0;min-width:180px}}
.time-btns{{display:flex;gap:4px;margin-bottom:2px}}
.tbtn{{background:transparent;border:1px solid #334155;color:#94a3b8;padding:3px 9px;border-radius:6px;cursor:pointer;font-size:.78rem;transition:all .2s}}
.tbtn.active,.tbtn:hover{{background:#334155;color:#e2e8f0;border-color:#475569}}
.cur-chart-wrap{{flex:1;min-width:240px;height:140px;position:relative}}
.cur-converter{{display:flex;align-items:center;gap:14px;margin-top:18px;padding-top:18px;border-top:1px solid #334155;flex-wrap:wrap}}
.conv-grp{{display:flex;flex-direction:column;gap:6px;flex:1;min-width:180px}}
.conv-lbl{{font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em}}
.conv-row{{display:flex;gap:6px}}
.conv-row input{{flex:1;background:#243347;border:1px solid #4a5e7a;border-radius:8px;color:#ffffff;padding:9px 12px;font-size:1rem;outline:none;min-width:0}}
.conv-row input:focus{{border-color:#60a5fa}}
.conv-row select{{background:#243347;border:1px solid #4a5e7a;border-radius:8px;color:#94a3b8;padding:8px 10px;font-size:.82rem;outline:none;cursor:pointer;min-width:200px}}
.swap-btn{{background:#334155;border:none;color:#e2e8f0;font-size:1.1rem;width:38px;height:38px;border-radius:50%;cursor:pointer;flex-shrink:0;transition:background .2s;align-self:flex-end;margin-bottom:2px}}
.swap-btn:hover{{background:#475569}}
/* Weather tab */
.weather-list{{display:flex;flex-direction:column;gap:10px}}
.wc-card{{display:flex;align-items:stretch;background:#1e293b;border-radius:14px;overflow:hidden;transition:transform .2s,box-shadow .2s}}
.wc-card:hover{{transform:translateX(5px);box-shadow:0 4px 20px rgba(0,0,0,.4)}}
.wc-left-panel{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;background:#172033;padding:20px 22px;min-width:110px;flex-shrink:0}}
.wc-emoji{{font-size:2.6rem;line-height:1}}
.wc-temprow{{display:flex;align-items:baseline;gap:2px}}
.wc-temp{{font-size:1.8rem;font-weight:700;color:#e2e8f0}}
.wc-unit{{font-size:.8rem;color:#64748b}}
.wc-right-panel{{flex:1;padding:14px 20px;display:flex;flex-direction:column;gap:5px;min-width:0}}
.wc-city{{font-size:1.6rem;font-weight:700;color:#60a5fa;letter-spacing:.01em}}
.wc-desc{{font-size:.8rem;color:#94a3b8}}
.wc-stats{{font-size:.75rem;color:#64748b}}
.wc-chart-wrap{{height:60px}}
.wc-forecast{{display:flex;gap:2px;padding-top:8px;border-top:1px solid #334155}}
.wc-day{{flex:1;display:flex;flex-direction:column;align-items:center;gap:1px}}
.wc-day-name{{font-size:.65rem;color:#64748b}}
.wc-day-icon{{font-size:.9rem}}
.wc-day-hi{{font-size:.72rem;color:#e2e8f0;font-weight:600}}
.wc-day-lo{{font-size:.68rem;color:#64748b}}
/* Choices.js dark theme */
.choices{{flex:1;min-width:180px}}
.choices__inner{{background:#243347!important;border:1px solid #4a5e7a!important;border-radius:8px!important;padding:5px 10px!important;min-height:38px!important}}
.choices__single{{color:#ffffff!important;font-size:.82rem!important;padding:0!important;margin-bottom:0!important;line-height:24px!important}}
.choices__list--single{{padding:0!important}}
.choices[data-type*=select-one]:after{{border-color:#64748b transparent transparent!important}}
.choices[data-type*=select-one].is-open:after{{border-color:transparent transparent #64748b!important}}
.choices__list--dropdown,.choices__list[aria-expanded]{{background:#1e293b!important;border:1px solid #334155!important;border-radius:8px!important;margin-top:4px!important;z-index:99!important}}
.choices__list--dropdown .choices__item,.choices__list[aria-expanded] .choices__item{{color:#94a3b8!important;font-size:.82rem!important;padding:8px 12px!important}}
.choices__list--dropdown .choices__item--selectable.is-highlighted,.choices__list[aria-expanded] .choices__item--selectable.is-highlighted{{background:#334155!important;color:#e2e8f0!important}}
.choices__input{{background:#0f172a!important;color:#e2e8f0!important;font-size:.82rem!important;border-bottom:1px solid #334155!important;padding:6px 12px!important;margin-bottom:4px!important;width:100%!important}}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/choices.js@10/public/assets/styles/choices.min.css">
<script src="https://cdn.jsdelivr.net/npm/choices.js@10/public/assets/scripts/choices.min.js"></script>
</head>
<body>

<div class="tabs">
  <div class="tab active" onclick="show('places',this)">🌍 Explore the World</div>
  <div class="tab" onclick="show('food',this)">🍽️ Food</div>
  <div class="tab" onclick="show('weather',this)">🌤️ Weather</div>
  <div class="tab" onclick="show('map',this)">🗺️ Map</div>
</div>

<div class="header">
  <div class="header-left">
    <div class="flag">{info['flag_emoji']}</div>
    <div class="country-name">
      <h1>{name}</h1>
      <p>{info['region']} &nbsp;·&nbsp; {info['subregion']}</p>
      {f'<p style="color:#ffffff;margin-top:8px;font-size:.9rem;line-height:1.7">{description}</p>' if description else ''}
    </div>
  </div>
</div>

<div class="carousel-wrap">
  <button class="carr-btn carr-prev" onclick="carrMove(-1)">&#8592;</button>
  <div class="carousel-viewport">
    <div class="carousel-track" id="carTrack">
      {carousel_items}
    </div>
  </div>
  <button class="carr-btn carr-next" onclick="carrMove(1)">&#8594;</button>
</div>

<div class="stats">
  <div class="stat"><div class="val">{info['capital']}</div><div class="lbl">Capital</div></div>
  <div class="stat"><div class="val">{pop}</div><div class="lbl">Population</div></div>
  <div class="stat"><div class="val">{currency}</div><div class="lbl">Currency</div></div>
  <div class="stat"><div class="val">{lang}</div><div class="lbl">Language</div></div>
</div>

<div class="currency-section">
  <div class="currency-top">
    <div class="currency-left">
      <div class="time-btns">
        <button class="tbtn" onclick="fetchHist('1W',this)">1W</button>
        <button class="tbtn active" onclick="fetchHist('1M',this)">1M</button>
        <button class="tbtn" onclick="fetchHist('3M',this)">3M</button>
        <button class="tbtn" onclick="fetchHist('6M',this)">6M</button>
        <button class="tbtn" onclick="fetchHist('1Y',this)">1Y</button>
      </div>
    </div>
    <div class="cur-chart-wrap">
      <canvas id="currencyChart"></canvas>
    </div>
  </div>
  <div class="cur-converter">
    <div class="conv-grp">
      <span class="conv-lbl">Amount</span>
      <div class="conv-row">
        <input type="number" id="convAmt" value="1" min="0" oninput="doConvert()">
        <select id="convFrom" onchange="doConvert()">
          <option value="{currency_code.lower()}">{currency_name_full}</option>
        </select>
      </div>
    </div>
    <button class="swap-btn" onclick="doSwap()">⇌</button>
    <div class="conv-grp">
      <span class="conv-lbl">Converted</span>
      <div class="conv-row">
        <input type="number" id="convResult" readonly placeholder="—">
        <select id="convTo" onchange="doConvert()">
          <option value="usd">US Dollar</option>
        </select>
      </div>
    </div>
  </div>
</div>

<div class="content">
  <div class="panel active" id="places"><div class="grid-6">{place_cards}</div></div>
  <div class="panel" id="food"><div class="food-list">{food_cards}</div></div>
  <div class="panel" id="weather"><div class="weather-list">{weather_cards_html}</div></div>
  <div class="panel" id="map"><div id="leaflet-map" class="map-container"></div></div>
</div>

<script>
// 3-up carousel
const track=document.getElementById('carTrack');
let carrPos=0;
function carrMove(dir){{
  const items=track.children;
  const total=items.length;
  const visible=3;
  const maxPos=total-visible;
  carrPos=Math.max(0,Math.min(maxPos,carrPos+dir));
  const itemW=items[0].offsetWidth+12;
  track.style.transform=`translateX(-${{carrPos*itemW}}px)`;
}}
// Tabs
function show(id,el){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
  if(id==='map')setTimeout(function(){{_initTgMap();if(_tgMap)_tgMap.invalidateSize();}},60);
}}
// Map — Leaflet.js
var _tgMap=null;
function _initTgMap(){{
  if(_tgMap)return;
  _tgMap=L.map('leaflet-map',{{zoomControl:true,attributionControl:true}}).setView([{lat},{lng}],{map_zoom});
  var voyager=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png',{{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
    subdomains:'abcd',maxZoom:20
  }});
  var osmLayer=L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
    maxZoom:19
  }});
  var satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{
    attribution:'Tiles &copy; Esri &mdash; Esri, Maxar, GeoEye, Earthstar Geographics',
    maxZoom:19
  }});
  var labelsOverlay=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png',{{
    subdomains:'abcd',maxZoom:20,opacity:0.9,
    attribution:''
  }});
  voyager.addTo(_tgMap);
  var baseMaps={{'🗺️ Street (Voyager)':voyager,'🗺️ OpenStreetMap':osmLayer,'🛰️ Satellite':satellite}};
  var overlays={{'🏷️ Labels (satellite)':labelsOverlay}};
  L.control.layers(baseMaps,overlays,{{position:'topright',collapsed:false}}).addTo(_tgMap);
  L.control.scale({{imperial:false,position:'bottomleft'}}).addTo(_tgMap);
  // Country boundary from Nominatim
  fetch('https://nominatim.openstreetmap.org/search?q='+encodeURIComponent({name_js})+'&limit=1&polygon_geojson=1&format=json')
    .then(function(r){{return r.json();}})
    .then(function(data){{
      if(data&&data[0]&&data[0].geojson){{
        L.geoJSON(data[0].geojson,{{
          style:{{color:'#60a5fa',weight:2.5,opacity:0.85,fillColor:'#3b82f6',fillOpacity:0.07}}
        }}).addTo(_tgMap);
      }}
    }})
    .catch(function(){{}});
  // City markers
  var _mc={weather_cities_js};
  _mc.forEach(function(c){{
    var popup='<div style="font-family:-apple-system,sans-serif;padding:4px 2px;min-width:100px">'+
      '<b style="font-size:.95rem;color:#0f172a">📍 '+c.city+'</b></div>';
    L.circleMarker([c.lat,c.lng],{{
      radius:9,fillColor:'#60a5fa',color:'#1d4ed8',weight:2.5,opacity:1,fillOpacity:0.9
    }}).addTo(_tgMap).bindPopup(popup);
  }});
  // Country centre label
  L.marker([{lat},{lng}],{{
    icon:L.divIcon({{
      className:'',
      html:'<div style="background:rgba(15,23,42,.88);color:#e2e8f0;padding:5px 11px;border-radius:8px;border:1.5px solid #60a5fa;font-weight:700;font-size:.82rem;white-space:nowrap;box-shadow:0 3px 12px rgba(0,0,0,.5)">'+{name_js}+'</div>',
      iconAnchor:[50,14]
    }})
  }}).addTo(_tgMap);
}}
// Currency Dashboard — fawazahmed0 API (150+ currencies)
var _CC='{currency_code.lower()}',_curChart=null,_fromC=null,_toC=null;
var _FAWAZ='https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@';
var _cOpts={{searchEnabled:true,searchPlaceholderValue:'Type to search...',itemSelectText:'',shouldSort:false,searchResultLimit:30}};
function _loadCurrencies(){{
  fetch(_FAWAZ+'latest/v1/currencies.json')
    .then(function(r){{return r.json();}})
    .then(function(data){{
      var codes=Object.keys(data).filter(function(c){{return /^[a-z]{{3}}$/.test(c);}}).sort();
      var arr=codes.map(function(c){{return {{value:c,label:c.toUpperCase()+' — '+data[c]}};}});
      if(_fromC){{_fromC.destroy();_fromC=null;}}
      if(_toC){{_toC.destroy();_toC=null;}}
      _fromC=new Choices(document.getElementById('convFrom'),Object.assign({{}},_cOpts));
      _fromC.setChoices(arr,'value','label',true);
      _fromC.setChoiceByValue(_CC==='usd'?'eur':_CC);
      _toC=new Choices(document.getElementById('convTo'),Object.assign({{}},_cOpts));
      _toC.setChoices(arr,'value','label',true);
      _toC.setChoiceByValue('usd');
      doConvert();
    }})
    .catch(function(){{}});
}}
function _initCur(){{
  _loadCurrencies();
  fetchHist('1M',document.querySelector('.tbtn.active'));
}}
function fetchHist(period,btn){{
  document.querySelectorAll('.tbtn').forEach(function(b){{b.classList.remove('active');}});
  if(btn)btn.classList.add('active');
  var today=new Date(),start=new Date(today),step;
  if(period==='1W'){{start.setDate(today.getDate()-7);step=1;}}
  else if(period==='1M'){{start.setMonth(today.getMonth()-1);step=7;}}
  else if(period==='3M'){{start.setMonth(today.getMonth()-3);step=14;}}
  else if(period==='6M'){{start.setMonth(today.getMonth()-6);step=21;}}
  else{{start.setFullYear(today.getFullYear()-1);step=30;}}
  function fmtD(x){{return x.toISOString().split('T')[0];}}
  var dates=[],c=new Date(start);
  while(c<=today){{dates.push(fmtD(c));c.setDate(c.getDate()+step);}}
  if(dates[dates.length-1]!==fmtD(today))dates.push(fmtD(today));
  var fc=_CC==='usd'?'eur':_CC;
  Promise.all(dates.map(function(dt){{
    return fetch(_FAWAZ+dt+'/v1/currencies/'+fc+'.json')
      .then(function(r){{return r.json();}})
      .then(function(d){{return {{dt:dt,v:(d[fc]&&d[fc]['usd'])||null}};}})
      .catch(function(){{return {{dt:dt,v:null}};}});
  }})).then(function(res){{
    var ok=res.filter(function(x){{return x.v!==null;}});
    _renderCurChart(ok.map(function(x){{return x.dt;}}),ok.map(function(x){{return x.v;}}));
  }});
}}
function _renderCurChart(labels,data){{
  var ctx=document.getElementById('currencyChart').getContext('2d');
  if(_curChart)_curChart.destroy();
  var up=data[data.length-1]>=data[0],col=up?'#34d399':'#f87171';
  _curChart=new Chart(ctx,{{
    type:'line',
    data:{{labels:labels,datasets:[{{data:data,borderColor:col,
      backgroundColor:up?'rgba(52,211,153,0.12)':'rgba(248,113,113,0.12)',
      borderWidth:2,pointRadius:0,fill:true,tension:0.4}}]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{
        legend:{{display:false}},
        tooltip:{{mode:'index',intersect:false,callbacks:{{label:function(c){{return c.parsed.y.toFixed(6)+' USD';}}}}}}
      }},
      scales:{{
        x:{{ticks:{{color:'#64748b',maxTicksLimit:6,font:{{size:10}}}},grid:{{color:'rgba(51,65,85,0.5)'}}}},
        y:{{ticks:{{color:'#64748b',font:{{size:10}}}},grid:{{color:'rgba(51,65,85,0.5)'}}}}
      }}
    }}
  }});
}}
function doConvert(){{
  var amt=parseFloat(document.getElementById('convAmt').value)||0;
  var from=document.getElementById('convFrom').value.toLowerCase();
  var to=document.getElementById('convTo').value.toLowerCase();
  if(from===to){{document.getElementById('convResult').value=amt.toFixed(4);return;}}
  fetch(_FAWAZ+'latest/v1/currencies/'+from+'.json')
    .then(function(r){{return r.json();}})
    .then(function(d){{
      var rate=d[from]&&d[from][to];
      if(rate)document.getElementById('convResult').value=(amt*rate).toFixed(4);
    }})
    .catch(function(){{}});
}}
function doSwap(){{
  if(!_fromC||!_toC)return;
  var tmp=document.getElementById('convFrom').value;
  _fromC.setChoiceByValue(document.getElementById('convTo').value);
  _toC.setChoiceByValue(tmp);
  doConvert();
}}
_initCur();
// Weather
var _WCITIES={weather_cities_js};
var _wcCharts={{}};
function _wEmoji(c){{
  if(c===0)return'☀️';if(c<=2)return'🌤️';if(c<=3)return'⛅';
  if(c<=48)return'🌫️';if(c<=57)return'🌦️';if(c<=67)return'🌧️';
  if(c<=77)return'❄️';if(c<=82)return'🌦️';return'⛈️';
}}
function _wDesc(c){{
  if(c===0)return'Clear sky';if(c===1)return'Mainly clear';if(c===2)return'Partly cloudy';
  if(c===3)return'Overcast';if(c<=48)return'Foggy';if(c<=57)return'Drizzle';
  if(c<=67)return'Rainy';if(c<=77)return'Snowy';if(c<=82)return'Showers';return'Thunderstorm';
}}
function _renderWCard(i,d){{
  var cur=d.current,daily=d.daily,hourly=d.hourly;
  document.getElementById('wemoji-'+i).textContent=_wEmoji(cur.weathercode);
  document.getElementById('wtemp-'+i).textContent=Math.round(cur.temperature_2m);
  document.getElementById('wdesc-'+i).textContent=_wDesc(cur.weathercode);
  document.getElementById('wstats-'+i).innerHTML=
    '💧 '+cur.relative_humidity_2m+'% &nbsp;💨 '+Math.round(cur.windspeed_10m)+' km/h &nbsp;🌧 '+cur.precipitation+'mm';
  var days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],fhtml='';
  for(var j=0;j<Math.min(7,daily.time.length);j++){{
    var dt=new Date(daily.time[j]+'T12:00:00');
    fhtml+='<div class="wc-day"><div class="wc-day-name">'+days[dt.getDay()]+'</div>'+
      '<div class="wc-day-icon">'+_wEmoji(daily.weathercode[j])+'</div>'+
      '<div class="wc-day-hi">'+Math.round(daily.temperature_2m_max[j])+'°</div>'+
      '<div class="wc-day-lo">'+Math.round(daily.temperature_2m_min[j])+'°</div></div>';
  }}
  document.getElementById('wforecast-'+i).innerHTML=fhtml;
  var now=new Date(),nowH=now.getHours();
  var hLabels=hourly.time.slice(nowH,nowH+24).map(function(t){{return t.split('T')[1].slice(0,5);}});
  var hTemps=hourly.temperature_2m.slice(nowH,nowH+24);
  var ctx=document.getElementById('wchart-'+i).getContext('2d');
  if(_wcCharts[i])_wcCharts[i].destroy();
  _wcCharts[i]=new Chart(ctx,{{
    type:'line',
    data:{{labels:hLabels,datasets:[{{data:hTemps,borderColor:'#f59e0b',
      backgroundColor:'rgba(245,158,11,0.15)',borderWidth:2,pointRadius:0,fill:true,tension:0.4}}]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:function(c){{return c.parsed.y.toFixed(1)+'°C';}}}}}}}},
      scales:{{
        x:{{ticks:{{color:'#64748b',maxTicksLimit:6,font:{{size:9}}}},grid:{{display:false}}}},
        y:{{ticks:{{color:'#64748b',font:{{size:9}},callback:function(v){{return v+'°';}}}},grid:{{color:'rgba(51,65,85,0.4)'}}}}
      }}
    }}
  }});
}}
(function(){{
  if(!_WCITIES.length)return;
  var baseUrl='https://api.open-meteo.com/v1/forecast?current=temperature_2m,relative_humidity_2m,precipitation,weathercode,windspeed_10m&hourly=temperature_2m&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=7&wind_speed_unit=kmh';
  Promise.all(_WCITIES.map(function(c,i){{
    return fetch(baseUrl+'&latitude='+c.lat+'&longitude='+c.lng)
      .then(function(r){{return r.json();}})
      .then(function(d){{_renderWCard(i,d);}})
      .catch(function(){{document.getElementById('wdesc-'+i).textContent='Unavailable';}});
  }}));
}})();
</script>
</body>
</html>"""

    _log(f"Rendering HTML ({len(all_photo_items)} carousel photos, {len(places)} places, {len(food)} dishes)")
    HTML_OUT.write_text(html, encoding="utf-8")
    _log(f"Saved → {HTML_OUT.name}")
    webbrowser.open(f"file://{HTML_OUT.absolute()}")
    return f"Travel page for {name} is open in your browser!"


if __name__ == "__main__":
    mcp.run()
