"""
Travel Guide Agent
Orchestrates MCP tool calls to build a travel guide page.
Uses Groq to generate a travel description shown on the page.
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

HERE = Path(__file__).parent
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_travel_description(country: str) -> str:
    """Use Groq to generate a short travel description for the country."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a 4-sentence travel description for {country}. "
                    "Make it inspiring and highlight what makes it special. "
                    "No markdown, plain text only."
                ),
            }
        ],
        max_tokens=180,
    )
    return response.choices[0].message.content.strip()


def get_place_names(country: str) -> str:
    """Use Groq to get 30 specific famous landmarks as a JSON array."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": (
                    f'List 30 specific famous tourist attractions in {country}. '
                    'Reply with ONLY a JSON array of strings using the exact Wikipedia article name. '
                    f'Example for France: ["Eiffel Tower", "Louvre Museum", "Palace of Versailles", "Mont Saint-Michel", "Notre-Dame de Paris", "Arc de Triomphe"]'
                ),
            }
        ],
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


def get_country_facts(country: str) -> str:
    """Use Groq to get quick travel facts as JSON."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Reply with ONLY a JSON object with these exact keys: "
                    "best_time (e.g. 'Apr–Oct'), visa (e.g. 'Visa required' or 'Visa on arrival' or 'Visa free'), "
                    "known_for (2–3 words, e.g. 'Temples, Sushi'), safety (e.g. 'Very safe' or 'Safe' or 'Take caution'). "
                    "No extra text."
                ),
            },
            {"role": "user", "content": f"Give travel facts for {country}."},
        ],
        max_tokens=80,
    )
    return response.choices[0].message.content.strip()


def get_cuisine_name(country: str) -> str:
    """Use Groq to get the correct TheMealDB cuisine name for a country."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Reply with ONLY the cuisine name from this list (exact spelling): "
                    "American, British, Canadian, Chinese, Croatian, Dutch, Egyptian, "
                    "Filipino, French, Greek, Indian, Irish, Italian, Jamaican, Japanese, "
                    "Kenyan, Malaysian, Mexican, Moroccan, Polish, Portuguese, Russian, "
                    "Spanish, Thai, Tunisian, Turkish, Ukrainian, Uruguayan, Vietnamese. "
                    "If not on the list, reply Unknown."
                ),
            },
            {"role": "user", "content": f"What is the cuisine name for {country}?"},
        ],
        max_tokens=10,
    )
    return response.choices[0].message.content.strip()


def get_dish_names(country: str) -> str:
    """Use Groq to get 15 famous dish names for any country's cuisine."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": (
                f"List 15 famous traditional dishes from {country}. "
                "Reply with ONLY a JSON array of dish name strings, "
                "using the exact Wikipedia article name where possible. "
                f'Example for Afghanistan: ["Kabuli pulao", "Mantu", "Bolani", "Ashak", "Shorwa"]'
            ),
        }],
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def get_top_cities(country: str) -> str:
    """Use Groq to get the top 15 tourist cities in a country as a JSON array."""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": (
                f"List the top 15 most visited tourist cities in {country}. "
                "Reply with ONLY a JSON array of city name strings. "
                f"Example for France: [\"Paris\", \"Lyon\", \"Nice\", \"Marseille\", \"Bordeaux\"]"
            ),
        }],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def _sep(): print("  " + "·" * 46)


async def run(country: str):
    server_params = StdioServerParameters(
        command="python",
        args=[str(HERE / "mcp_server.py")],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to Travel MCP server")
            _sep()

            # Step 1: Country info
            print("\n[1/5] 🌐 Fetching country info")
            print("      → MCP tool call: get_country_info")
            print(f"      → API: restcountries.com/v3.1/name/{country}")
            r = await session.call_tool("get_country_info", {"country_name": country})
            country_info = r.content[0].text
            info = json.loads(country_info)
            pop = f"{info['population']:,}"
            print(f"      ✓ {info['name']} · {info['region']} · Pop: {pop}")
            print(f"      ✓ Capital: {info['capital']} · Currency: {(info['currencies'] or ['?'])[0]}")

            # Step 2: Top places
            print("\n[2/5] 📍 Finding top places to visit")
            print("      → Groq AI (llama-3.3-70b): generating 30 landmark names...")
            place_names_json = get_place_names(country)
            try:
                plist = json.loads(place_names_json)
                pcount = len(plist)
                print(f"      ✓ AI returned {pcount} landmarks  e.g. {', '.join(plist[:3])}...")
            except Exception:
                pcount = 0
            print("      → MCP tool call: get_top_places")
            print(f"      → API: en.wikipedia.org (batch image fetch, {pcount} titles)")
            print(f"      → API: en.wikipedia.org (batch description fetch, {pcount} titles)")
            r = await session.call_tool("get_top_places", {"place_names_json": place_names_json})
            places = r.content[0].text if r.content else "[]"
            try:
                count = len(json.loads(places))
            except Exception:
                places = "[]"
                count = 0
            print(f"      ✓ {count}/{pcount} places loaded with photos")

            # Step 3: Local food
            print("\n[3/6] 🍽️  Finding local food")
            print("      → Groq AI (llama-3.3-70b): identifying cuisine type...")
            cuisine = get_cuisine_name(country)
            print(f"      ✓ Cuisine: {cuisine}")
            if cuisine != "Unknown":
                print("      → MCP tool call: get_local_food")
                print(f"      → API: themealdb.com/filter.php?a={cuisine}")
                r = await session.call_tool("get_local_food", {"cuisine": cuisine})
                food = r.content[0].text
            else:
                print("      → Not in TheMealDB — switching to Groq + Wikipedia fallback")
                print("      → Groq AI: generating dish names for this cuisine...")
                dish_names_json = get_dish_names(country)
                try:
                    dnames = json.loads(dish_names_json)
                    print(f"      ✓ AI returned {len(dnames)} dish names — e.g. {', '.join(dnames[:3])}...")
                except Exception:
                    pass
                print("      → MCP tool call: get_food_by_names")
                print("      → API: en.wikipedia.org (photos + descriptions)")
                r = await session.call_tool("get_food_by_names", {"dish_names_json": dish_names_json})
                food = r.content[0].text
            dish_count = len(json.loads(food))
            print(f"      ✓ {dish_count} dishes loaded")

            # Step 4: Weather
            print("\n[4/6] 🌤️  Fetching weather for top cities")
            print("      → Groq AI (llama-3.3-70b): getting top 15 cities...")
            cities_json = get_top_cities(country)
            try:
                cities_list = json.loads(cities_json)
                ccount = len(cities_list)
                print(f"      ✓ AI returned {ccount} cities — e.g. {', '.join(cities_list[:4])}...")
            except Exception:
                cities_json = "[]"
                ccount = 0
            print("      → MCP tool call: get_city_coords")
            print(f"      → API: geocoding-api.open-meteo.com ({ccount} cities)")
            r = await session.call_tool("get_city_coords", {
                "country_name": country, "cities_json": cities_json
            })
            weather_json = r.content[0].text
            wcount = len(json.loads(weather_json))
            print(f"      ✓ {wcount} cities geocoded (weather loads live in browser)")

            # Step 5: Wishlist
            print("\n[5/6] 💾 Saving to wishlist")
            print("      → MCP tool call: save_to_wishlist")
            print(f"      → Writing to: data/countries.json")
            r = await session.call_tool(
                "save_to_wishlist",
                {"country_name": country, "info_json": country_info},
            )
            print(f"      ✓ {r.content[0].text}")

            # Step 6: Build page
            print("\n[6/6] 🏗️  Generating travel guide page")
            print("      → Groq AI (llama-3.3-70b): writing travel description...")
            description = get_travel_description(country)
            print("      ✓ Description ready (4 sentences)")
            print("      → API: en.wikipedia.org (country scenery photos)")
            print("      → MCP tool call: build_travel_page")
            print("      → Rendering HTML + opening in browser...")
            r = await session.call_tool(
                "build_travel_page",
                {
                    "country_info_json": country_info,
                    "places_json": places,
                    "food_json": food,
                    "weather_json": weather_json,
                    "description": description,
                },
            )
            print(f"      ✓ {r.content[0].text}")

            _sep()
            print(f"\n🌍  Your {country} travel guide is ready!\n")


def main():
    import sys
    if len(sys.argv) > 1:
        country = " ".join(sys.argv[1:]).strip()
    else:
        print("\n🌍  Travel Guide Generator")
        print("─" * 40)
        country = input("\nWhich country do you want to explore? ").strip()
        if not country:
            country = "France"
    print(f"\n{'─'*40}")
    print(f"  Destination : {country}")
    print(f"  Model       : Groq llama-3.3-70b-versatile")
    print(f"  Transport   : MCP stdio")
    print(f"{'─'*40}\n")
    asyncio.run(run(country))


if __name__ == "__main__":
    main()
