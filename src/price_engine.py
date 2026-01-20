import requests
import time
import re
from urllib.parse import quote

class PriceEngine:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })    
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

    def search_snapcaster(self, card_name, quantity):
        """Search Snapcaster.ca for a card using their JSON API"""
        try:
            search_url = f"https://api.snapcaster.ca/api/v1/catalog/search?mode=singles&tcg=mtg&region=ca&keyword={quote(card_name)}&sortBy=price-asc&maxResultsPerPage=100&pageNumber=1"
            response = self.session.get(search_url, timeout=10)
            data = response.json()
            results = data.get('data', {}).get('results', [])
            best_result = None
            for product in results:
                title = product.get('name', '')
                if card_name.lower() in title.lower():
                    price = product.get('price')
                    vendor = product.get('vendor', 'Unknown')
                    set_name = product.get('set', 'Unknown')
                    link = product.get('link', search_url)
                    condition = product.get('condition', 'Unknown')
                    printing = product.get('printing', 'Unknown')
                    # Snapcaster does not provide explicit stock, but if price exists, it's in stock
                    in_stock = price is not None
                    if in_stock:
                        total_cost = price * quantity
                        result = {
                            'store': f'Snapcaster ({vendor})',
                            'card_name': title,
                            'set': set_name,
                            'price': price,
                            'in_stock': in_stock,
                            'stock_info': condition,
                            'total_cost': total_cost,
                            'url': link,
                            'printing': printing
                        }
                        # Return the first (cheapest) in-stock result
                        return result
            return None
        except Exception as e:
            print(f"Error searching Snapcaster for {card_name}: {e}")
            return None

    def search_jeuxjubes(self, card_name, quantity):
        """Search JeuxJubes via Shopify suggest API (if available)"""
        try:
            search_url = f"https://www.mtgjeuxjubes.com/search/suggest.json?q={quote(card_name)}&resources[type]=product"

            response = self.session.get(search_url, timeout=10)
            data = response.json()
            products = data.get("resources", {}).get("results", {}).get("products", [])

            cheapest = None

            for product in products:
                title = product.get("title", "")
                available = product.get("available", False)
                price_str = product.get("price_max", "0")

                if card_name.lower() in title.lower() and available:
                    try:
                        price = float(price_str)
                    except ValueError:
                        continue  # skip if price is not a number

                    product_url = product.get("url", "")
                    total_cost = price * quantity

                    # Keep the cheapest available product
                    if cheapest is None or price < cheapest["price"]:
                        cheapest = {
                            "store": "JeuxJubes",
                            "card_name": title,
                            "price": price,
                            "in_stock": True,
                            "stock_info": "Available online",
                            "total_cost": total_cost,
                            "url": f"https://www.jeuxjubes.com{product_url}"
                        }

            return cheapest

        except Exception as e:
            print(f"Error searching JeuxJubes for {card_name}: {e}")
            return None     

    def search_401games(self, card_name, quantity):
        """Search 401games.ca for a card using their Shopify API"""
        try:
            # 401 Games uses FastSimon API for search
            # request_source and src are required to enable fulltext search
            search_url = f"https://api.fastsimon.com/full_text_search?request_source=v-next&src=v-next&UUID=d3cae9c0-9d9b-4fe3-ad81-873270df14b5&store_id=17041809&q={quote(card_name)}&narrow=[[%22In+Stock%22,%22True%22]]&page_num=1&products_per_page=40"

            response = self.session.get(search_url, timeout=10)
            data = response.json()

            # Parse the API response
            if 'items' in data and len(data['items']) > 0:
                for item in data['items']:
                    title = item.get('l', '')  # 'l' appears to be the title field
                    if card_name.lower() in title.lower():
                        # Price is in 'p' field
                        price = float(item.get('p', 0))

                        # Since we filtered for in stock, assume it's available
                        in_stock = True

                        # Get product URL
                        product_url = item.get('u', '')
                        if product_url and not product_url.startswith('http'):
                            product_url = f"https://store.401games.ca{product_url}"

                        return {
                            'store': '401 Games',
                            'card_name': title,
                            'price': price,
                            'in_stock': in_stock,
                            'stock_info': 'In Stock',
                            'total_cost': price * quantity,
                            'url': product_url or f"https://store.401games.ca/pages/search-results?q={quote(card_name)}"
                        }

            return None
        except Exception as e:
            print(f"Error searching 401 Games for {card_name}: {e}")
            return None

    def search_facetoface(self, card_name, quantity):
        """Search Face to Face Games for a card using their JSON API"""
        try:
            search_url = f"https://facetofacegames.com/apps/prod-indexer/search/pageSize/24/page/1/keyword/{quote(card_name)}/Availability/In%2520Stock"
            response = self.session.get(search_url, timeout=10)
            data = response.json()
            hits = data.get('hits', {}).get('hits', [])
            best_result = None
            best_price = float('inf')
            for hit in hits:
                source = hit.get('_source', {})
                title = source.get('title', '')
                if card_name.lower() in title.lower():
                    set_name = source.get('Set') or source.get('MTG_Set_Name', 'Unknown')
                    url = f"https://facetofacegames.com/products/{source.get('handle', '')}"
                    for variant in source.get('variants', []):
                        price = variant.get('price')
                        inventory = variant.get('inventoryQuantity', 0)
                        if price is not None and inventory > 0:
                            # Get condition from selectedOptions
                            condition = 'Unknown'
                            for opt in variant.get('selectedOptions', []):
                                if opt.get('name', '').lower() == 'condition':
                                    condition = opt.get('value', 'Unknown')
                                    break
                            printing = source.get('Finish', 'Unknown')
                            total_cost = price * quantity
                            if price < best_price:
                                best_price = price
                                best_result = {
                                    'store': 'Face to Face Games',
                                    'card_name': title,
                                    'set': set_name,
                                    'price': price,
                                    'in_stock': True,
                                    'stock_info': f"{condition} ({inventory} in stock)",
                                    'total_cost': total_cost,
                                    'url': url,
                                    'printing': printing
                                }
            return best_result
        except Exception as e:
            print(f"Error searching Face to Face for {card_name}: {e}")
            return None

    def search_all_stores(self, card_name, quantity):
        """Search all stores for a card and return results"""
        print(f"\nSearching for: {card_name} (Qty: {quantity})")

        results = []

        # Search each store with a small delay to be respectful
        snapcaster_result = self.search_snapcaster(card_name, quantity)
        if snapcaster_result:
            results.append(snapcaster_result)
        time.sleep(1)

        jeuxjubes_result = self.search_jeuxjubes(card_name, quantity)
        if jeuxjubes_result:
            results.append(jeuxjubes_result)
        time.sleep(1)

        games_401_result = self.search_401games(card_name, quantity)
        if games_401_result:
            results.append(games_401_result)
        time.sleep(1)

        facetoface_result = self.search_facetoface(card_name, quantity)
        if facetoface_result:
            results.append(facetoface_result)
        time.sleep(1)

        return results

    def process_card_list(self, card_list):
        """
        Process a list of cards with quantities
        card_list format: [{'name': 'Card Name', 'quantity': 4}, ...]
        """

        all_results = {}

        total = len(card_list)

        for i, card in enumerate(card_list):
            card_name = card['name']
            quantity = card['quantity']

            # 👉 UPDATE PROGRESS
            self.last_progress = int(((i + 1) / total) * 100)

            results = self.search_all_stores(card_name, quantity)
            all_results[card_name] = {
                'quantity': quantity,
                'results': results
            }

        # When finished:
        self.last_progress = 100

        return all_results

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
