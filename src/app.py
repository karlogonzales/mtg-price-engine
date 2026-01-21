from flask import Flask, render_template, request, jsonify
import asyncio

from price_engine import PriceEngine

app = Flask(__name__, template_folder="templates")

checker = PriceEngine()

@app.route("/", methods=["GET", "POST"])
def index():
    card_list_parsed = None
    results = None

    if request.method == "POST":
        text = request.form.get("card_list_text", "")

        # Parse cards (still sync)
        card_list_parsed = checker.parse_card_list(text)

        # 🔥 CALL ASYNC ENGINE FROM FLASK
        results = asyncio.run(
            checker.process_card_list_async(card_list_parsed)
        )

    return render_template(
        "index.html",
        card_list_parsed=card_list_parsed,
        results=results
    )

@app.route("/progress")
def progress():
    return jsonify({"percent": checker.last_progress})

if __name__ == "__main__":
    app.run(debug=True)
