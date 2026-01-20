# MTG Price Engine

MTG Price Engine is a web application that allows users to check Magic: The Gathering (MTG) card prices across multiple Canadian online stores. Paste your card list, and the app will fetch the best available prices and stock information from several vendors.

## Features
- Paste a list of MTG cards and quantities (e.g., `2 Sol Ring`)
- Parses your list and queries multiple Canadian MTG stores:
  - Snapcaster
  - JeuxJubes
  - 401 Games
  - Face to Face Games
- Displays prices, stock status, and links to product pages
- Progress bar for long lookups

## Project Structure
```
mtg-price-engine/
  src/
    app.py
    price_engine.py
    templates/
      index.html
  resources/
  examples/
    card_list_test.txt
  requirements.txt
  README.md
```

## How It Works
- The app is built with Flask (Python web framework)
- The core logic is in `src/price_engine.py`, which handles parsing and store queries
- The web interface is in `src/app.py` and `src/templates/index.html`

## Prerequisites
- **Python 3.8 or newer** is required. If you do not have Python installed:
  - On macOS: Python 3 is often pre-installed. To install or upgrade, use [Homebrew](https://brew.sh/):
    ```bash
    brew install python
    ```
  - On Windows: Download and install from the [official Python website](https://www.python.org/downloads/).
  - On Linux: Use your distribution's package manager, e.g.:
    ```bash
    sudo apt-get install python3
    ```

## Usage
1. **Create and activate a virtual environment (recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # .\venv\Scripts\activate  # On Windows
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the app:**
   ```bash
   cd src
   python app.py
   ```
4. **Open your browser:**
   Go to [http://127.0.0.1:5000](http://127.0.0.1:5000)
5. **Paste your card list** and click "Check Prices"

## Card List Format
Paste your cards in the following format:
```
2 Sol Ring
1 Counterspell
4 Lightning Bolt
```

## File Overview
- `src/app.py`: Flask web server
- `src/price_engine.py`: Card parsing and price lookup logic
- `src/templates/index.html`: Web UI template
- `requirements.txt`: Python dependencies
- `examples/card_list_test.txt`: Example/test card list

## Notes
- This tool is for informational purposes. Prices and stock may change.
- Only supports Canadian stores listed above.

## License
MIT License
