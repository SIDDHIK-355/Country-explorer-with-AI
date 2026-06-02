"""
Travel Guide search page built with Prefab UI.
Call build_html(photos_b64) to get the full HTML string.
"""
import json

from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, H1, Muted, Text
from prefab_ui.components.div import Div
from prefab_ui.components.input import Input
from prefab_ui.actions import Fetch, SetState
from prefab_ui.rx import Rx, RESULT


def build_html(photos_b64: list[str]) -> str:
    country_input = Input(
        placeholder="Search any country... (e.g. Japan, Brazil, Egypt)",
        name="country",
        css_class="tg-input",
    )
    status = Rx("status")

    search_action = [
        SetState("status", "✈️  Generating your travel guide..."),
        Fetch.post(
            "/run",
            body={"country": "{{ country }}"},
            on_success=SetState("status", "{{ $result.message }}"),
            on_error=SetState("status", "❌  Something went wrong. Please try again."),
        ),
    ]

    custom_css = """
html, body {
    margin: 0; padding: 0; min-height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
#root {
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    min-height: 100vh;
}
body {
    background-color: #0f1b2d;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    transition: background-image 1.5s ease-in-out;
    min-height: 100vh;
}
.tg-page {
    min-height: 100vh;
    background: linear-gradient(160deg, rgba(5,10,25,0.60) 0%, rgba(0,20,50,0.70) 100%);
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 48px 20px;
    backdrop-filter: blur(2px);
}
.tg-title {
    font-size: 4.2rem;
    font-weight: 300;
    color: #ffffff;
    letter-spacing: -2px;
    text-align: center;
    margin: 0 0 10px 0;
    text-shadow: 0 2px 24px rgba(0,0,0,0.55);
}
.tg-subtitle {
    color: rgba(255,255,255,0.65);
    font-size: 1.0rem;
    text-align: center;
    margin: 0 0 44px 0;
    text-shadow: 0 1px 8px rgba(0,0,0,0.6);
    letter-spacing: 0.02em;
}
.tg-form {
    width: 100%;
    max-width: 580px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
}
/* Override Prefab's Input styles */
.tg-form .tg-input,
.tg-form input[type="text"],
.tg-form input {
    width: 100% !important;
    padding: 16px 24px !important;
    font-size: 1.1rem !important;
    border: none !important;
    border-radius: 32px !important;
    background: rgba(255,255,255,0.97) !important;
    box-shadow: 0 4px 28px rgba(0,0,0,0.35) !important;
    outline: none !important;
    color: #1a1a2e !important;
    caret-color: #1a73e8;
}
.tg-form input:focus {
    box-shadow: 0 4px 36px rgba(79,195,247,0.40) !important;
}
/* Override Prefab's Button styles */
.tg-form button {
    width: 100% !important;
    padding: 14px 32px !important;
    background: #1a73e8 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 32px !important;
    font-size: 1.05rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    box-shadow: 0 4px 18px rgba(26,115,232,0.45) !important;
    transition: background 0.2s, transform 0.12s !important;
    letter-spacing: 0.02em;
}
.tg-form button:hover {
    background: #1557b0 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(26,115,232,0.55) !important;
}
.tg-status-wrap {
    margin-top: 8px;
    min-height: 28px;
    text-align: center;
}
.tg-status-wrap p,
.tg-status-wrap span {
    color: rgba(255,255,255,0.88) !important;
    font-size: 0.95rem !important;
    text-shadow: 0 1px 6px rgba(0,0,0,0.5);
}
"""

    photos_json = json.dumps(photos_b64)
    bg_script = f"""
<script>
(function() {{
    var photos = {photos_json};
    if (!photos.length) return;
    var idx = 0;
    document.body.style.backgroundImage = 'url(' + photos[0] + ')';
    setInterval(function() {{
        idx = (idx + 1) % photos.length;
        document.body.style.backgroundImage = 'url(' + photos[idx] + ')';
    }}, 7000);
}})();
</script>
"""

    with PrefabApp(
        title="🌍 Travel Guide",
        state={"country": "", "status": ""},
        css=[custom_css],
    ) as app:
        with Div(css_class="tg-page"):
            with Column(gap=0):
                Text("🌍 Travel Guide", css_class="tg-title")
                Muted(
                    "Explore any country in the world",
                    css_class="tg-subtitle",
                )
                with Div(css_class="tg-form"):
                    country_input
                    Button("Search", on_click=search_action)
                    with Div(css_class="tg-status-wrap"):
                        Text(f"{status}")

    html = app.html()
    # Inject background-cycling script before </head>
    return html.replace("</head>", bg_script + "\n</head>")
