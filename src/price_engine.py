import asyncio
import aiohttp
import re
from urllib.parse import quote

class PriceEngine:
    def __init__(self):
        self.last_progress = 0

    def parse_card_list(self, text):
        """
        Parses a plain text card list and returns a list of dicts in the format:
        {'name': card_name, 'quantity': quantity}
        """
        cards = []

        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue  # skip empty lines

            # Match quantity at the start and card name after
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                quantity = int(match.group(1))
                card_name = match.group(2).strip()
                cards.append({
                    "name": card_name,
                    "quantity": quantity
                })
            else:
                print(f"Skipping unrecognized line: {line}")

        return cards

    async def search_snapcaster(self, session, card_name, quantity):
        try:
            search_url = (
                "https://api.snapcaster.ca/api/v1/catalog/search"
                f"?mode=singles&tcg=mtg&region=ca&keyword={quote(card_name)}"
                "&sortBy=price-asc&maxResultsPerPage=100&pageNumber=1"
            )

            async with session.get(search_url, timeout=10) as response:
                data = await response.json()

            results = data.get("data", {}).get("results", [])
            for product in results:
                normalized = product.get("normalized_name", "").lower()

                # 🚫 Ignore Art Cards
                if "art" in normalized and "card" in normalized:
                    continue

                title = product.get("name", "")
                price = product.get("price")

                if price and card_name.lower() in title.lower():
                    return {
                        "store": f"Snapcaster ({product.get('vendor', 'Unknown')})",
                        "card_name": title,
                        "price": price,
                        "in_stock": True,
                        "stock_info": product.get("condition", "Unknown"),
                        "total_cost": price * quantity,
                        "url": product.get("link"),
                    }

            return None

        except Exception as e:
            print(f"Snapcaster error ({card_name}): {e}")
            return None

    async def search_jeuxjubes(self, session, card_name, quantity):
        try:
            url = (
                "https://www.mtgjeuxjubes.com/search/suggest.json"
                f"?q={quote(card_name)}&resources[type]=product"
            )

            async with session.get(url, timeout=10) as resp:
                data = await resp.json()

            cheapest = None

            for product in data.get("resources", {}).get("results", {}).get("products", []):
                
                title = product.get("title", "")

                # 🚫 Ignore Art Cards
                if "art" in title.lower() and "card" in title.lower():
                    continue
                if not product.get("available"):
                    continue

                if card_name.lower() in title.lower():
                    price = float(product.get("price_max", 0))
                    if price <= 0:
                        continue

                    if cheapest is None or price < cheapest["price"]:
                        cheapest = {
                            "store": "JeuxJubes",
                            "card_name": title,
                            "price": price,
                            "in_stock": True,
                            "stock_info": "Available online",
                            "total_cost": price * quantity,
                            "url": f"https://www.jeuxjubes.com{product.get('url', '')}",
                        }

            return cheapest
        except Exception as e:
            print(f"JeuxJubes error ({card_name}): {e}")
            return None
     

    async def search_401games(self, session, card_name, quantity):
        try:
            url = (
                f"https://api.fastsimon.com/full_text_search?request_source=v-next&src=v-next&UUID=d3cae9c0-9d9b-4fe3-ad81-873270df14b5&store_id=17041809&q={quote(card_name)}&narrow=[[%22In+Stock%22,%22True%22]]&page_num=1&products_per_page=40"
            )

            async with session.get(url, timeout=10) as resp:
                data = await resp.json(content_type=None)

            for item in data.get("items", []):
                title = item.get("l", "")
                if card_name.lower() in title.lower():
                    price = float(item.get("p", 0))
                    url = item.get("u", "")

                    if url and not url.startswith("http"):
                        url = f"https://store.401games.ca{url}"

                    return {
                        "store": "401 Games",
                        "card_name": title,
                        "price": price,
                        "in_stock": True,
                        "stock_info": "In Stock",
                        "total_cost": price * quantity,
                        "url": url,
                    }

            return None
        except Exception as e:
            print(f"401 Games error ({card_name}): {e}")
            return None

    async def search_facetoface(self, session, card_name, quantity):
        try:
            url = (
                "https://facetofacegames.com/apps/prod-indexer/search"
                f"/pageSize/24/page/1/keyword/{quote(card_name)}"
                "/Availability/In%2520Stock"
            )

            async with session.get(url, timeout=10) as resp:
                data = await resp.json()

            best = None
            best_price = float("inf")

            for hit in data.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                title = src.get("title", "")

                if card_name.lower() not in title.lower():
                    continue

                for variant in src.get("variants", []):
                    price = variant.get("price")
                    inventory = variant.get("inventoryQuantity", 0)

                    if price and inventory > 0 and price < best_price:
                        best_price = price
                        best = {
                            "store": "Face to Face Games",
                            "card_name": title,
                            "price": price,
                            "in_stock": True,
                            "stock_info": f"{inventory} in stock",
                            "total_cost": price * quantity,
                            "url": f"https://facetofacegames.com/products/{src.get('handle', '')}",
                        }

            return best
        except Exception as e:
            print(f"FaceToFace error ({card_name}): {e}")
            return None


    async def search_all_stores(self, session, card_name, quantity, store_sem):
        async with store_sem:
            tasks = [
                self.search_snapcaster(session, card_name, quantity),
                self.search_jeuxjubes(session, card_name, quantity),
                self.search_401games(session, card_name, quantity),
                self.search_facetoface(session, card_name, quantity),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if r and not isinstance(r, Exception)]


    async def process_card_list_async(self, card_list):
        total = len(card_list)
        self.last_progress = 0

        card_sem = asyncio.Semaphore(5)
        store_sem = asyncio.Semaphore(5)

        async with aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0"}
        ) as session:

            async def run_card(i, card):
                async with card_sem:
                    results = await self.search_all_stores(
                        session, card["name"], card["quantity"], store_sem
                    )
                    self.last_progress = int(((i + 1) / total) * 100)
                    return card["name"], {
                        "quantity": card["quantity"],
                        "results": results
                    }

            tasks = [
                run_card(i, card)
                for i, card in enumerate(card_list)
            ]

            data = await asyncio.gather(*tasks)

        self.last_progress = 100
        return dict(data)


    def display_results(self, all_results):
        """Display results in a readable format"""
        print("\n" + "="*80)
        print("SEARCH RESULTS")
        print("="*80)

        for card_name, data in all_results.items():
            quantity = data['quantity']
            results = data['results']

            print(f"\n{card_name} (Qty: {quantity})")
            print("-" * 80)

            if not results:
                print("  Not found in any store")
                continue

            # Sort by total cost
            results.sort(key=lambda x: x['total_cost'])

            for result in results:
                status = "✓ In Stock" if result['in_stock'] else "✗ Out of Stock"
                print(f"  {result['store']:20} | ${result['price']:6.2f} each | Total: ${result['total_cost']:7.2f} | {status}")

        print("\n" + "="*80)
        self.calculate_best_deal(all_results)

    def calculate_best_deal(self, all_results):
        """Calculate the best overall deal per store"""
        print("\nBEST DEAL PER STORE (for in-stock items only):")
        print("-" * 80)

        store_totals = {}

        for card_name, data in all_results.items():
            for result in data['results']:
                if result['in_stock']:
                    store = result['store']
                    if store not in store_totals:
                        store_totals[store] = {'total': 0, 'cards': []}
                    store_totals[store]['total'] += result['total_cost']
                    store_totals[store]['cards'].append(f"{card_name} (${result['price']:.2f} x {data['quantity']})")

        if not store_totals:
            print("No cards available in stock.")
            return

        # Sort by total cost
        sorted_stores = sorted(store_totals.items(), key=lambda x: x[1]['total'])

        for store, info in sorted_stores:
            print(f"\n{store}: ${info['total']:.2f}")
            for card in info['cards']:
                print(f"  - {card}")
