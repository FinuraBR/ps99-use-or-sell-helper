# PS99 Use-or-Sell Helper

A lightweight, terminal-based Python tool designed to help Pet Simulator 99 players resolve a constant dilemma: **"Should I use this item, or should I sell it on the Plaza?"**

By interfacing with the `ps99rap.com` API, this script analyzes real-time market data, calculates stable price trends, and evaluates the expected utility value of your items.

---

## 📊 How It Works

*   **🔍 Universal Dynamic Lookup:** Search and analyze market stats (Current RAP, 24h High/Low, and daily variation) for any tradeable item in Pet Simulator 99.
*   **📈 Multi-Trend Analysis & Manipulation Sentry:** Calculates medians across 3 timeframes (24h, 7D, and 30D). It uses the **7-Day Median** as the "golden standard" to protect you from short-term clan manipulation while adapting perfectly to the game's weekly update cycle.
*   **👑 Expected Value (EV) Engine:** Uses modular rules in `item_blueprints.json` to calculate if the actual worth of possible drop rates (keys, lootboxes, gifts) exceeds the market selling price.
*   **💰 Dynamic Pricing Tiers:** Stop guessing what to charge. The script suggests tailored Plaza booth prices (**Quick Sell, Fair Value, and Max Profit**) depending on the item's stable price and whether it's currently being manipulated.
*   **🕒 Interactive Session History:** Keeps a local, fast-access history of your searched items during your active session. You can re-examine a spec sheet instantly using the index number, requiring zero redundant network calls.

---

## 💡 Why I Started This Project

I originally started this project for a simple, personal reason: I wanted to know if a specific item in my inventory was worth using, how much I should list it for if I decided to sell, and what its actual progression value was. Manually keeping track of median prices, drop rates, and opportunity costs was tedious, so I wrote a script to automate it.

However, I believe this tool can be useful to the entire Pet Simulator 99 community. Every player faces the same questions when looking at their inventory, and having a quick, data-driven reference can help anyone optimize their gems and progress faster.

---

## 🤝 Contributing

This project is a work-in-progress. If you have better data for drop rates, encounter bugs, or want to add a new "VIP" item formula, feel free to open a Pull Request or submit an Issue.

---

## 📦 Setup & Installation

1.  **Prerequisites:** Python 3.x and the `requests` library.
    ```bash
    pip install requests
    ```
2.  **Run:** Clone this repository, place `ps99-ev-analyzer.py` and `item_blueprints.json` in the same directory, and run:
    ```bash
    python ps99-ev-analyzer.py
    ```

---

## 📜 Disclaimer

This is a personal hobby project. It uses publicly available data from `ps99rap.com`. While it calculates mathematical averages (Expected Value), it cannot guarantee in-game luck. Always double-check trade plaza booths before making major decisions.
