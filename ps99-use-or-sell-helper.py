import json
import os
import sys
import time

APP_VERSION = "v0.2.1"

try:
    import requests
except ImportError:
    print("\n❌ SYSTEM ERROR: The 'requests' library is not installed.")
    print("To fix this, run the following command in your terminal:")
    print("  pip install requests")
    sys.exit(1)

APP_CACHE = {
    "items_data": None,
    "stats": {},
    "searched_items": []
}

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

BLUEPRINTS_FILE = os.path.join(SCRIPT_DIR, "item_blueprints.json")

def load_blueprints():
    if not os.path.exists(BLUEPRINTS_FILE):
        print("\n❌ CONFIGURATION ERROR: The definition file was not found.")
        print(f"Please make sure 'item_blueprints.json' is in: {BLUEPRINTS_FILE}")
        sys.exit(1)
        
    try:
        with open(BLUEPRINTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("\n❌ SYNTAX ERROR: Failed to read 'item_blueprints.json'.")
        print(f"Error details: {e}")
        sys.exit(1)

ITEM_BLUEPRINTS = load_blueprints()

def format_gems(value):
    if value == 9999999999:
        return "Infinite (ROI)"
    if abs(value) < 1000:
        return f"{value} gems"
    if abs(value) < 1000000:
        return f"{value/1000:.1f}k"
    if abs(value) < 1000000000:
        return f"{value/1000000:.2f}M"
    return f"{value/1000000000:.2f}B"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def calculate_median(lst):
    if not lst: return 0
    sorted_lst = sorted(lst)
    n = len(sorted_lst)
    return sorted_lst[n // 2] if n % 2 == 1 else (sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) / 2.0

def calculate_history_stats(history_list):
    if not history_list: return {}
    history_list = sorted(history_list, key=lambda x: x[0])
    is_ms = history_list[0][0] > 1e11
    now_ts = time.time() * 1000 if is_ms else time.time()
    
    one_day = 24 * 60 * 60 * 1000 if is_ms else 24 * 60 * 60
    one_week = 7 * 24 * 60 * 60 * 1000 if is_ms else 7 * 24 * 60 * 60
    one_month = 30 * 24 * 60 * 60 * 1000 if is_ms else 30 * 24 * 60 * 60
    
    raps_all = [point[1] for point in history_list]
    raps_24h = [point[1] for point in history_list if now_ts - point[0] <= one_day]
    raps_7d = [point[1] for point in history_list if now_ts - point[0] <= one_week]
    raps_30d = [point[1] for point in history_list if now_ts - point[0] <= one_month]
    
    current_rap = raps_all[-1]
    
    median_24h = calculate_median(raps_24h if raps_24h else raps_all)
    median_7d = calculate_median(raps_7d if raps_7d else raps_all)
    median_30d = calculate_median(raps_30d if raps_30d else raps_all)
    
    high_24h = max(raps_24h) if raps_24h else current_rap
    low_24h = min(raps_24h) if raps_24h else current_rap
    
    if raps_24h:
        first_rap_24h = raps_24h[0]
        change_24h = current_rap - first_rap_24h
        pct_change_24h = (change_24h / first_rap_24h * 100) if first_rap_24h > 0 else 0
    else:
        change_24h, pct_change_24h = 0, 0
        
    return {
        "current_rap": current_rap,
        "stable_price": median_7d,
        "median_24h": median_24h,
        "median_7d": median_7d,
        "median_30d": median_30d,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "change_24h": change_24h,
        "pct_change_24h": pct_change_24h,
        "all_time_high": max(raps_all)
    }

def fetch_ps99rap_data():
    url = "https://ps99rap.com/api/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        return {}

def fetch_rap_histories(item_slugs):
    if not item_slugs: return {}
    slugs_string = ",".join(item_slugs)
    url = f"https://ps99rap.com/api/items/rap_histories?ids={slugs_string}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"\n❌ HISTORY ERROR: {e}")
        return {}

def find_item_id(items_data, target_name, target_category):
    aliases = {
        "Charms": ["Charms", "Charm"],
        "Lootboxes": ["Lootboxes", "Lootbox", "Gifts", "Gift"],
        "Keys": ["Keys", "Key"],
        "ZoneFlags": ["ZoneFlags", "Flags", "Flag"],
        "Vouchers": ["Vouchers", "Voucher", "MiscItems"],
        "MiscItems": ["MiscItems", "Misc", "Tools"],
        "Pet": ["Pet", "Pets"]
    }
    allowed = [c.lower() for c in aliases.get(target_category, [target_category])]
    for k, v in items_data.items():
        if v.get("name", "").lower() == target_name.lower() and v.get("category", "").lower() in allowed:
            return k
    for k, v in items_data.items():
        if v.get("name", "").lower() == target_name.lower():
            return k
    return None

def ensure_item_data_loaded(targets):
    global APP_CACHE
    if APP_CACHE["items_data"] is None:
        print("\n⏳ Syncing API mapping...")
        APP_CACHE["items_data"] = fetch_ps99rap_data()
        if not APP_CACHE["items_data"]: return False, {}
            
    items_data = APP_CACHE["items_data"]
    slugs_to_fetch = []
    item_to_slug = {}
    
    for category, name in targets:
        slug = find_item_id(items_data, name, category)
        if slug:
            item_to_slug[(category, name)] = slug
            if slug not in APP_CACHE["stats"]:
                slugs_to_fetch.append(slug)
            
    if slugs_to_fetch:
        print(f"⏳ Downloading new data via API...")
        fetched = fetch_rap_histories(slugs_to_fetch)
        if not fetched: return False, {}
        for slug, raw_history in fetched.items():
            APP_CACHE["stats"][slug] = calculate_history_stats(raw_history)
    else:
        print("⚡ [Cache] Loaded from memory!")
        time.sleep(0.3)
    return True, item_to_slug

def get_cached_stable_price(category, name):
    global APP_CACHE
    if APP_CACHE["items_data"]:
        slug = find_item_id(APP_CACHE["items_data"], name, category)
        if slug and slug in APP_CACHE["stats"]:
            return APP_CACHE["stats"][slug].get("stable_price")
    return None

def get_blueprint_dependencies(item_name):
    blueprint = ITEM_BLUEPRINTS.get(item_name)
    if not blueprint: return []
    deps = [(blueprint["category"], item_name)]
    for dep in blueprint["dependencies"]:
        deps.append((dep["category"], dep["name"]))
    return deps

def calculate_dynamic_blueprint(item_name):
    blueprint = ITEM_BLUEPRINTS.get(item_name)
    if not blueprint: return None
    ev = blueprint["base_value"]
    dep_prices = {}
    for i, dep in enumerate(blueprint["dependencies"]):
        price = get_cached_stable_price(dep["category"], dep["name"])
        if price is None:
            print(f"\n❌ MARKET ERROR: Missing price for '{dep['name']}'.")
            return None
        ev += dep["multiplier"] * price
        dep_prices[f"dep_{i}_price"] = format_gems(price)
    try:
        desc = blueprint["desc_template"].format(**dep_prices)
    except:
        desc = blueprint["desc_template"]
    return {"ev": ev, "type": blueprint["type"], "desc": desc}

def display_item_details(item_name, category, slug):
    stats = APP_CACHE["stats"].get(slug)
    if not stats or "current_rap" not in stats or "stable_price" not in stats:
        clear_screen()
        print("="*80)
        print(f" SPEC SHEET: {item_name.upper()} ({category})")
        print("="*80 + "\n")
        print(f"❌ MARKET ERROR: Incomplete data for '{item_name}'.")
        return False
        
    rap_atual = stats["current_rap"]
    preco_estavel = stats["stable_price"]
    
    med_24h = stats.get("median_24h", 0)
    med_7d = stats.get("median_7d", 0)
    med_30d = stats.get("median_30d", 0)
    
    is_blueprint = item_name in ITEM_BLUEPRINTS
    
    if is_blueprint:
        analysis = calculate_dynamic_blueprint(item_name)
        if not analysis: return False
        ev, item_type, desc = analysis["ev"], analysis["type"], analysis["desc"]
        decision = "SELL EXCESS" if item_type == "tool" else ("SELL" if preco_estavel > ev else "USE")
            
    clear_screen()
    print("="*80)
    print(f" SPEC SHEET: {item_name.upper()} ({category})")
    print(f" Status: {'👑 VIP [BLUEPRINT]' if is_blueprint else '🌐 STANDARD [API]'}")
    print("="*80 + "\n")
    
    if is_blueprint:
        print(f"1. Use Value (Intrinsic EV): {format_gems(ev)}")
        print(f"   Drop Details: {desc}\n")
        print(f"2. Sell Value (Market Stats):")
        print(f"   ├─ Current RAP: {format_gems(rap_atual)}")
        print(f"   ├─ 24H Median (Volatile): {format_gems(med_24h)}")
        print(f"   ├─ 7D Median (Stable/Recommended): {format_gems(med_7d)} ⭐")
        print(f"   └─ 30D Median (Long-Term Trend): {format_gems(med_30d)}\n")
    else:
        print(f"1. Market Stats:")
        print(f"   ├─ Current RAP: {format_gems(rap_atual)}")
        print(f"   ├─ 24H Median (Volatile): {format_gems(med_24h)}")
        print(f"   ├─ 7D Median (Stable/Recommended): {format_gems(med_7d)} ⭐")
        print(f"   ├─ 30D Median (Long-Term Trend): {format_gems(med_30d)}")
        print(f"   ├─ 24h Change: {stats.get('pct_change_24h', 0):.2f}%")
        print(f"   └─ All-Time High: {format_gems(stats.get('all_time_high', 0))}\n")
        
    sec = "3" if is_blueprint else "2"
    print(f"{sec}. Risk Analysis:")
    is_manip = preco_estavel > 0 and rap_atual > 1.30 * preco_estavel
    if is_manip:
        print(f"   ⚠️ WARNING: RAP manipulated! (+{((rap_atual-preco_estavel)/preco_estavel)*100:.1f}% vs 7D Median)")
    else:
        print(f"   ✅ Price is stable against the 7-day median.")
    
    if is_blueprint and item_type in ["gambling", "trap_charm"]:
        loss = ((preco_estavel - ev) / preco_estavel) * 100 if preco_estavel > 0 else 0
        print(f"   ⚠️ Opening is gambling. Expected Loss: {loss:.1f}%")
        
    print(f"\n{int(sec)+1}. Final Verdict: [{decision if is_blueprint else 'MARKET-DRIVEN'}]")
    
    if preco_estavel > 0:
        fast_price = int(preco_estavel * 0.97)
        std_price = int(preco_estavel)
        max_price = int(preco_estavel * 1.03) if not is_manip else int(rap_atual * 0.99)
        
        print(f"   Suggested Booth Prices:")
        print(f"   ├── [1] Quick Sell (-3%): {format_gems(fast_price)}")
        print(f"   ├── [2] Fair Value  (0%): {format_gems(std_price)}")
        print(f"   └── [3] Max Profit (+3%): {format_gems(max_price)}")
    else:
        print("   └── Insufficient data to suggest prices.")
        
    print("="*80)
    return True

def run_analysis():
    while True:
        clear_screen()
        print("="*80)
        print(f" 🏆 NAVIGATION CENTER | Version: {APP_VERSION}")
        print("="*80)
        print("  [1] 🔍 Search Item\n  [2] 🕒 Session History\n" + "-"*40 + "\n  [0] Exit")
        print("="*80)
        
        opt = input("👉 Select: ").strip()
        if opt == "0": break
        elif opt == "1":
            clear_screen()
            query = input("\n👉 Search: ").strip().lower()
            if not query: continue
            if APP_CACHE["items_data"] is None:
                APP_CACHE["items_data"] = fetch_ps99rap_data()
            
            res = [(s, i.get("name"), i.get("category")) for s, i in APP_CACHE["items_data"].items() if query in i.get("name", "").lower()]
            if not res:
                input("\n❌ No results. Press ENTER.")
                continue
                
            for i, (s, n, c) in enumerate(res[:15]): print(f"  [{i}] {n} ({c})")
            ch = input("\n👉 Index: ").strip()
            if ch.isdigit() and int(ch) < len(res[:15]):
                slug, name, cat = res[int(ch)]
                deps = get_blueprint_dependencies(name) if name in ITEM_BLUEPRINTS else [(cat, name)]
                success, _ = ensure_item_data_loaded(deps)
                if success and display_item_details(name, cat, slug):
                    if (name, cat, slug) not in APP_CACHE["searched_items"]:
                        APP_CACHE["searched_items"].append((name, cat, slug))
                input("\nPress ENTER.")
        elif opt == "2":
            while True:
                clear_screen()
                print(" 🕒 SESSION HISTORY")
                history = APP_CACHE.get("searched_items", [])
                if not history:
                    input("\nNo history yet. Press ENTER."); break
                print(f" {'Idx':<4} | {'Item':<22} | {'RAP':<11} | {'7D Median':<11}")
                for i, (n, c, s) in enumerate(history):
                    st = APP_CACHE["stats"].get(s, {})
                    print(f" [{i:<2}] | {n:<20} | {format_gems(st.get('current_rap',0)):<11} | {format_gems(st.get('stable_price',0)):<11}")
                ch = input("\n👉 Select Idx to review (or ENTER to return): ").strip()
                if not ch: break
                if ch.isdigit() and int(ch) < len(history):
                    n, c, s = history[int(ch)]
                    display_item_details(n, c, s)
                    input("\nPress ENTER.")

if __name__ == "__main__":
    try: run_analysis()
    except KeyboardInterrupt: print("\nExiting...")
