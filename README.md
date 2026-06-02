# 🌍 Travel Guide App

An AI-powered travel guide generator. Type any country name and get a rich, browser-based travel guide — complete with landmark photos, local food, live weather, an interactive map, and real-time currency conversion.

---

## Built With

| Layer | Technology | Role |
|---|---|---|
| **AI Agent** | [Groq](https://groq.com) — `llama-3.3-70b-versatile` | Generates landmark names, dish names, top cities, and travel descriptions |
| **Tool Calling** | [MCP](https://modelcontextprotocol.io) (Model Context Protocol) | Structured communication between the agent and the data-fetching tools |
| **MCP Server** | [FastMCP](https://github.com/jlowin/fastmcp) | Exposes 7 tools the agent calls over stdio (`get_country_info`, `get_top_places`, `get_local_food`, `get_food_by_names`, `get_city_coords`, `save_to_wishlist`, `build_travel_page`) |
| **MCP Transport** | stdio | Agent spawns the MCP server as a subprocess and communicates via stdin/stdout |
| **UI Framework** | [Prefab UI](https://prefabui.com) | Builds the search page declaratively in Python — no HTML/JS written by hand |
| **Web Server** | Python `http.server` (ThreadingHTTPServer) | Serves the search page and triggers the agent on POST `/run` |
| **Frontend** | Vanilla JS + [Chart.js](https://www.chartjs.org) + [Leaflet.js](https://leafletjs.com) + [Choices.js](https://joshuajohnson.co.uk/Choices/) | Weather charts, interactive map, currency converter dropdown |

### MCP Tool Calling — How It Works Here

The agent (`agent.py`) and the server (`mcp_server.py`) are two separate processes connected by MCP over stdio:

```
agent.py  ──[MCP stdio]──▶  mcp_server.py
   │                              │
   │  call_tool("get_country_info", {...})
   │  call_tool("get_top_places", {...})
   │  call_tool("get_local_food", {...})
   │  call_tool("get_city_coords", {...})
   │  call_tool("save_to_wishlist", {...})
   │  call_tool("build_travel_page", {...})
   ▼                              ▼
 Groq AI                    External APIs
(llama-3.3-70b)        (Wikipedia, RestCountries,
                         TheMealDB, Open-Meteo)
```

The agent decides **what** to fetch (using Groq to generate names and parameters), then calls the right MCP tool to actually fetch it. Each tool is a plain Python function decorated with `@mcp.tool()` in `mcp_server.py`.

---

## How AI Is Used

This app uses Groq's `llama-3.3-70b-versatile` model — called **5 times** per country search:

| Call | What AI does | What happens next |
|---|---|---|
| **Landmark names** | Generates 30 specific famous landmarks (e.g. `"Fushimi Inari Shrine"`) | Wikipedia fetches real photos + descriptions for each |
| **Cuisine type** | Maps the country to a TheMealDB cuisine name (e.g. `"Japan"` → `"Japanese"`) | TheMealDB fetches dish photos; if unsupported, AI generates dish names instead |
| **Top 15 cities** | Picks the most visited tourist cities for the country | Open-Meteo geocodes them → powers weather cards and map markers |
| **Travel description** | Writes a 4-sentence inspiring description of the country | Displayed under the country name on the guide page |
| **Country facts** | Returns a JSON object with `best_time`, `visa`, `known_for`, `safety` | Displayed as travel quick-facts |

> **The key idea:** AI doesn't generate the final page — it generates the right *search terms and parameters* so the MCP tools can fetch real data (photos, weather, food) from real APIs. Groq is the brain, MCP tools are the hands.

---

## How It Works

The app runs a local web server with a clean search page. When you search for a country, an AI agent kicks off a 6-step pipeline:

1. **Country info** — fetches official data (flag, capital, population, currency, languages) from [restcountries.com](https://restcountries.com)
2. **Top places** — Groq AI generates 30 famous landmarks, then Wikipedia provides photos and descriptions via batch API calls
3. **Local food** — TheMealDB supplies dish photos; if the cuisine isn't in their database, Groq generates dish names and Wikipedia fills in photos and descriptions
4. **Weather** — Groq picks the top 15 tourist cities, Open-Meteo geocodes them, and the browser fetches live forecasts
5. **Wishlist** — the country is saved to `data/countries.json` for later
6. **Travel page** — a full HTML guide is generated and opened in your browser

---

## Features

- **Photo carousel** — up to 30 scrollable photos (landmark shots + country scenery)
- **Explore the World tab** — iconic world landmarks with photos
- **Food tab** — horizontal dish cards with Wikipedia descriptions
- **Weather tab** — live current conditions, hourly chart, and 7-day forecast per city
- **Map tab** — interactive Leaflet map with country boundary, city markers, and satellite/street toggle
- **Currency dashboard** — historical exchange rate chart (1W / 1M / 3M / 6M / 1Y) and a live converter supporting 150+ currencies
- **Search page background** — cycles through your own photos from the `Photo/` folder

---

## Project Structure

```
travel_app/
├── run_app.py        # HTTP server — serves the search page, triggers the agent
├── prefab_app.py     # Search page UI built with Prefab UI
├── agent.py          # AI agent — orchestrates all MCP tool calls
├── mcp_server.py     # FastMCP server — tools for data fetching and HTML generation
├── data/
│   └── countries.json  # Local wishlist (auto-created)
├── Photo/            # Background photos for the search page
└── travel_guide.html # Generated guide (overwritten each run)
```

---

## Prerequisites

- Python 3.10+
- A [Groq](https://console.groq.com) API key (free tier works)

---

## Setup

```bash
# 1. Install dependencies
pip install groq mcp fastmcp requests python-dotenv prefab-ui

# 2. Add your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env
```

---

## Running

```bash
python run_app.py
```

The search page opens automatically at `http://127.0.0.1:5175`. Type a country name, click **Search**, and your travel guide will open in a new browser tab in about 20–30 seconds.

You can also run the agent directly from the terminal:

```bash
python agent.py Japan
python agent.py "New Zealand"
```

---

## APIs Used

| Service | Purpose | Auth |
|---|---|---|
| [Groq](https://groq.com) — llama-3.3-70b | Landmark names, dish names, city lists, travel descriptions | API key (`.env`) |
| [restcountries.com](https://restcountries.com) | Country metadata | None |
| [Wikipedia API](https://en.wikipedia.org/w/api.php) | Photos and descriptions | None |
| [TheMealDB](https://www.themealdb.com) | Dish photos for supported cuisines | None |
| [Open-Meteo](https://open-meteo.com) | Geocoding + live weather forecasts | None |
| [fawazahmed0 Currency API](https://github.com/fawazahmed0/exchange-api) | Exchange rates (150+ currencies) | None |
| [OpenStreetMap / Leaflet](https://leafletjs.com) | Interactive map | None |
| [Nominatim](https://nominatim.openstreetmap.org) | Country boundary overlay | None |

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
