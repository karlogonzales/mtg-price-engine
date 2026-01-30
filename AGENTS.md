MTG Price Engine — Agent Guide
==============================

Concise guide for AI agents and developers to grasp scope, structure, and conventions of this repo.

Overview
- Purpose: Flask web app to parse a pasted MTG card list, query Canadian stores, and surface best prices/stock with links.
- Stores: Snapcaster, JeuxJubes, 401 Games, Face to Face Games, Hobbiesville.
- Flow: paste list → parse → async store queries → progress polling → results with best prices highlighted.

Tech Stack
- Python 3.8+
- Flask (Jinja2 templating)
- asyncio + aiohttp
- Regex parsing; BeautifulSoup4 available (minimal use now)
- Frontend: single Jinja2 template with inline CSS/JS (no build tooling)

Architecture
- Web layer: src/app.py defines Flask app, routes `/` (GET/POST) and `/progress` (JSON progress).
- Engine: src/price_engine.py with PriceEngine (parsing, async store searches, progress tracking, result shaping).
- Template: src/templates/index.html (form, progress bar polling `/progress`, card results).
- Example input: examples/card_list_test.txt.

Key Components
- src/app.py
  - POST `/`: read `card_list_text`, parse via PriceEngine.parse_card_list, call process_card_list_async via asyncio.run.
  - `/progress`: returns `{percent: checker.last_progress}`.
  - Renders index.html with `card_list_parsed`, `results`.
- src/price_engine.py
  - parse_card_list(text): regex `^\d+\s+name` → list of `{name, quantity}` (skips bad lines with stdout notice).
  - search_snapcaster: Snapcaster API; filters art cards; builds URL using handle when present; vendor included in store label.
  - search_jeuxjubes: Shopify suggest API; skips art/unavailable; picks cheapest; URL prefixed with `https://www.mtgjeuxjubes.com`.
  - search_401games: FastSimon search; filters MTG SKUs; normalizes relative URLs.
  - search_facetoface: Product indexer; scans variants; filters MTG SKUs; picks cheapest in-stock with inventory info.
  - search_hobbiesville: Storepass API; skips art cards; requires stock>0 and price>0; picks cheapest (prints titles to stdout currently).
  - search_all_stores: gathers all five store coroutines; filters exceptions/None.
  - process_card_list_async: semaphores card_sem=5, store_sem=5; updates last_progress per card; returns `{card: {quantity, results[], found}}`.
  - display_results / calculate_best_deal: CLI helpers (not used in web flow).
- src/templates/index.html
  - Form posts to `/`; JS showLoading() polls `/progress` every 1s for the progress bar.
  - Renders parsed cards with status icons and anchors; store cards per result, first visually “best price”.

Data Flow
1) User submits textarea → POST `/`.
2) parse_card_list → list of `{name, quantity}`.
3) process_card_list_async → per card: search_all_stores (5 stores concurrently under semaphores).
4) Progress polled from `/progress`; template renders results when POST completes.

Concurrency & Limits
- Semaphores: card-level 5, store-level 5.
- Each store call timeout=10s; failures logged and return None; asyncio.gather with return_exceptions=True prevents cascade.

Error Handling
- Network/API errors: logged with store name and card; processing continues.
- Unrecognized lines skipped with stdout notice.
- Guards for missing links/price/SKU; art card heuristics applied where possible.

Store Result Schema
```
{
  "store": str,
  "card_name": str,
  "price": float,
  "in_stock": bool,
  "stock_info": str,
  "total_cost": float,  # price * quantity
  "url": str
}
```

Extending / Adding Stores
- Implement `async def search_<store>(session, card_name, quantity)` returning the schema above or None on failure.
- Add coroutine to the list in search_all_stores.
- Keep: 10s timeout, art-card filtering, MTG SKU validation when applicable, absolute URLs.

API Surface
- `/` GET/POST: form + results.
- `/progress` GET: `{percent}` for polling.
- Template context: `card_list_parsed`, `results` (dict of card → {quantity, results[], found}).

Conventions & Notes
- Prices as floats; total_cost = price * quantity.
- Progress stored in PriceEngine.last_progress (instance-level state).
- UI highlights first result per card as best price.
- Example input: examples/card_list_test.txt.
- README.md currently lists only four stores; Hobbiesville is present in code.

Development History (recent highlights)
- Added Hobbiesville store (f401f30) and merged (f589e27).
- Fixed Snapcaster URL construction with handle fallback (39a6972).
- Art-card filtering improvements for Snapcaster/JeuxJubes (7aa525e).

Potential Next Steps
- Update README.md to include Hobbiesville.
- Add tests (parsing and store search shaping with mocked APIs).
- Externalize store configs (URLs, timeouts, semaphore limits) and add retry/backoff.
- Normalize card names (handle set markers/special chars) before queries.
- Improve UI accessibility/mobile; surface per-card/store errors; remove debug prints (Hobbiesville titles).
