import json
import os
import sys
import time

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
        print("Please make sure that the 'item_blueprints.json' file is present in the following directory:")
        print(f"  {BLUEPRINTS_FILE}")
        sys.exit(1)
        
    try:
        with open(BLUEPRINTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("\n❌ SYNTAX ERROR: Failed to read the 'item_blueprints.json' file.")
        print("Please check if the file format is valid JSON (matching quotes, braces, and commas).")
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
    if not lst:
        return 0
    sorted_lst = sorted(lst)
    n = len(sorted_lst)
    if n % 2 == 1:
        return sorted_lst[n // 2]
    else:
        return (sorted_lst[n // 2 - 1] + sorted_lst[n // 2]) / 2.0

def calculate_history_stats(history_list):
    if not history_list:
        return {}
        
    history_list = sorted(history_list, key=lambda x: x[0])
    is_ms = history_list[0][0] > 1e11
    now_ts = time.time() * 1000 if is_ms else time.time()
    
    one_day = 24 * 60 * 60 * 1000 if is_ms else 24 * 60 * 60
    one_month = 30 * 24 * 60 * 60 * 1000 if is_ms else 30 * 24 * 60 * 60
    
    raps_all = [point[1] for point in history_list]
    raps_24h = [point[1] for point in history_list if now_ts - point[0] <= one_day]
    raps_30d = [point[1] for point in history_list if now_ts - point[0] <= one_month]
    
    working_30d_list = raps_30d if raps_30d else raps_all
    current_rap = raps_all[-1]
    
    stable_median_30d = calculate_median(working_30d_list)
    
    high_24h = max(raps_24h) if raps_24h else current_rap
    low_24h = min(raps_24h) if raps_24h else current_rap
    if raps_24h:
        first_rap_24h = raps_24h[0]
        change_24h = current_rap - first_rap_24h
        pct_change_24h = (change_24h / first_rap_24h * 100) if first_rap_24h > 0 else 0
    else:
        change_24h, pct_change_24h = 0, 0
        
    all_time_high = max(raps_all)
    
    return {
        "current_rap": current_rap,
        "stable_price": stable_median_30d,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "change_24h": change_24h,
        "pct_change_24h": pct_change_24h,
        "all_time_high": all_time_high
    }

def fetch_ps99rap_data():
    url_items = "https://ps99rap.com/api/items"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url_items, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: Failed to load the database. ({e})")
        return {}

def fetch_rap_histories(item_slugs):
    if not item_slugs:
        return {}
    slugs_string = ",".join(item_slugs)
    url_histories = f"https://ps99rap.com/api/items/rap_histories?ids={slugs_string}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url_histories, headers=headers, timeout=25)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"\n❌ HISTORY ERROR: Failed to download historical data. ({e})")
        return {}

def find_item_id(items_data, target_name, target_category):
    category_aliases = {
        "Charms": ["Charms", "Charm"],
        "Lootboxes": ["Lootboxes", "Lootbox", "Gifts", "Gift"],
        "Keys": ["Keys", "Key"],
        "ZoneFlags": ["ZoneFlags", "Flags", "Flag"],
        "Vouchers": ["Vouchers", "Voucher", "MiscItems"],
        "MiscItems": ["MiscItems", "Misc", "Tools"],
        "Pet": ["Pet", "Pets"]
    }
    allowed = [c.lower() for c in category_aliases.get(target_category, [target_category])]
    for k, v in items_data.items():
        name = v.get("name", "")
        category = v.get("category", "")
        if name.lower() == target_name.lower() and category.lower() in allowed:
            return k
    for k, v in items_data.items():
        if v.get("name", "").lower() == target_name.lower():
            return k
    return None

def ensure_item_data_loaded(targets):
    global APP_CACHE
    
    if APP_CACHE["items_data"] is None:
        print("\n⏳ Synchronizing general API mapping for the first time...")
        APP_CACHE["items_data"] = fetch_ps99rap_data()
        if not APP_CACHE["items_data"]:
            return False, {}
            
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
        print(f"⏳ Downloading new historical data via API...")
        fetched_histories = fetch_rap_histories(slugs_to_fetch)
        if not fetched_histories:
            return False, {}
            
        for slug, raw_history in fetched_histories.items():
            APP_CACHE["stats"][slug] = calculate_history_stats(raw_history)
    else:
        print("⚡ [Session Cache] Data loaded instantly from local memory!")
        time.sleep(0.5)
            
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
    if not blueprint:
        return []
    
    deps = [(blueprint["category"], item_name)]
    for dep in blueprint["dependencies"]:
        deps.append((dep["category"], dep["name"]))
    return deps

def calculate_dynamic_blueprint(item_name):
    blueprint = ITEM_BLUEPRINTS.get(item_name)
    if not blueprint:
        return None
        
    ev = blueprint["base_value"]
    dep_prices_formatted = {}
    
    for i, dep in enumerate(blueprint["dependencies"]):
        price = get_cached_stable_price(dep["category"], dep["name"])
    
        if price is None:
            print(f"\n❌ MARKET ERROR: Could not obtain stable price for dependency '{dep['name']}' ({dep['category']}).")
            return None
            
        ev += dep["multiplier"] * price
        dep_prices_formatted[f"dep_{i}_price"] = format_gems(price)
        
    try:
        desc = blueprint["desc_template"].format(**dep_prices_formatted)
    except KeyError:
        desc = blueprint["desc_template"]
        
    return {
        "ev": ev,
        "type": blueprint["type"],
        "desc": desc
    }

def display_item_details(item_name, category, slug):
    stats = APP_CACHE["stats"].get(slug)
    
    if not stats or "current_rap" not in stats or "stable_price" not in stats:
        clear_screen()
        print("==========================================================================")
        print(f"               📋 SPEC SHEET: {item_name.upper()} ({category})")
        print("==========================================================================\n")
        print(f"❌ MARKET ERROR: Incomplete historical data for '{item_name}' on the API.")
        print("Could not process stable price or RAP information.")
        print("==========================================================================")
        return False
        
    rap_atual = stats["current_rap"]
    preco_estavel = stats["stable_price"]
    
    is_blueprint = item_name in ITEM_BLUEPRINTS
    
    if is_blueprint:
        analysis = calculate_dynamic_blueprint(item_name)
        if not analysis:
            return False
            
        ev = analysis["ev"]
        item_type = analysis["type"]
        desc = analysis["desc"]
        
        if item_type == "tool":
            decision = "SELL EXCESS"
        else:
            decision = "SELL" if preco_estavel > ev else "USE"
            
    clear_screen()
    print("==========================================================================")
    print(f"               📋 SPEC SHEET: {item_name.upper()} ({category})")
    if is_blueprint:
        print("         👑 [REGISTERED ITEM] VIP Treatment & Active EV Analysis Active   ")
    else:
        print("         🌐 [STANDARD API ITEM] Active Market Statistical Analysis Active  ")
    print("==========================================================================\n")
    
    if is_blueprint:
        print("1. The \"Use/Open\" Value (Intrinsic EV):")
        if item_type == "trap_charm":
            print(f"   ├─ Utility Value (EV): {format_gems(0)}")
            print(f"   └─ Practical Impact: NEGATIVE. Occupying a slot with this item prevents using meta charms and devalues your Huge.")
        elif item_type == "voucher":
            print(f"   ├─ Estimated Daily Return: ~4.00k gems/day")
            print(f"   └─ Practical Impact: Extremely fast Return on Investment (ROI) of ~2.3 days. Permanent passive generation.")
        elif item_type == "tool":
            print(f"   ├─ Utility Value (EV): Dynamic (Equivalent to the value of the Charm you salvage).")
            print(f"   └─ Technical Criterion: Only worth using if the salvaged Charm is worth more than the Chisel cost ({format_gems(preco_estavel)}).")
        else:
            print(f"   ├─ Safe Expected Value (EV): {format_gems(ev)}")
            print(f"   └─ Drop Details: {desc}")
        print()
    else:
        print("1. General Market Data:")
        print(f"   ├─ Current Market Price (RAP): {format_gems(rap_atual)}")
        print(f"   ├─ Stable Organic Price (30D Median): {format_gems(preco_estavel)}")
        print(f"   ├─ All-Time High: {format_gems(stats.get('all_time_high', 0))}")
        print(f"   ├─ Variation in Last 24h: {stats.get('pct_change_24h', 0):.2f}%")
        print(f"   ├─ Peak (24h High): {format_gems(stats.get('high_24h', 0))}")
        print(f"   └─ Floor (24h Low): {format_gems(stats.get('low_24h', 0))}")
        print()
        
    if is_blueprint:
        print("2. The \"Sell\" Value (Opportunity Cost):")
        print(f"   ├─ Current Market Price (RAP): {format_gems(rap_atual)}")
        print(f"   ├─ Stable Organic Price (30D Median): {format_gems(preco_estavel)}")
        print(f"   └─ Opportunity Cost: Activating/Opening this item means discarding a guaranteed {format_gems(preco_estavel)}.")
        print()
        
    section_num = "3" if is_blueprint else "2"
    print(f"{section_num}. Risk vs. Reward Analysis:")
    is_manipulated = preco_estavel > 0 and rap_atual > 1.30 * preco_estavel
    if is_manipulated:
        dif_pct = ((rap_atual - preco_estavel) / preco_estavel) * 100
        print(f"   ⚠️  MANIPULATION DETECTED: The current RAP is artificially inflated by +{dif_pct:.1f}%!")
        print(f"       Recommended selling immediately to profit from the manipulation, but listing slightly below the current RAP.")
    elif not is_blueprint and preco_estavel > 0 and rap_atual < 0.70 * preco_estavel:
        dif_pct = ((preco_estavel - rap_atual) / preco_estavel) * 100
        print(f"   💸 FLIP OPPORTUNITY: The RAP is {dif_pct:.1f}% BELOW the 30-day stable price.")
    else:
        print(f"   ├─ Price Status: Price without manipulation anomalies (stability guaranteed).")
        
    if is_blueprint:
        if item_type in ["gambling", "trap_charm"]:
            print(f"   ├─ Risk Alert: Opening is GAMBLING. You are risking a guaranteed {format_gems(preco_estavel)} for an EV reward of only {format_gems(ev)}.")
            if preco_estavel > 0:
                perda_pct = ((preco_estavel - ev) / preco_estavel) * 100
                print(f"   └─ Expected Loss: Statistically, you will lose {perda_pct:.1f}% of the total value upon opening.")
        elif item_type == "buff":
            if preco_estavel > ev:
                print(f"   ├─ The market price ({format_gems(preco_estavel)}) is inflated due to hype and far exceeds the bonus return ({format_gems(ev)}).")
                print(f"   └─ Suggestion: Sell and secure the fixed profit.")
            else:
                print(f"   ├─ The booster cost ({format_gems(preco_estavel)}) is trivial compared to the additional gems generated during active farming ({format_gems(ev)}).")
                print(f"   └─ Suggestion: Always prefer to use to accelerate your wealth generation.")
        elif item_type == "tool":
            print("   ├─ Allocation Alert: Retaining more than 2 to 5 units is a financial inefficiency. Liquidate the excess.")
            print("   └─ Suggestion: Use only to rescue Royalty/Overload Charms.")
        else:
            print("   └─ Balanced stability. Practical value greatly exceeds the selling value.")
    print()
    
    section_num = "4" if is_blueprint else "3"
    if is_blueprint:
        print(f"{section_num}. Final Verdict: [{decision}]")
        if item_type == "tool":
             print("   ├─ Justification: Retaining expensive tools without active use wastes liquidity. Use only to rescue Royalty/Overload Charms.")
        elif decision == "SELL":
            print(f"   ├─ Justification: Preserving liquid and safe gems is mathematically superior to accepting the statistical loss.")
        else:
            print(f"   ├─ Justification: Activating the item yields an active farm return or passive income far superior to the selling value.")
            
    print(f"{section_num}. Suggested Prices for your Trade Plaza:")
    if preco_estavel > 0:
        fast_price = int(preco_estavel * 0.85) if preco_estavel > 5000 else int(preco_estavel * 0.80)
        std_price = int(preco_estavel * 0.95)
        max_price = int(preco_estavel * 1.05) if not is_manipulated else int(rap_atual * 0.98)
        print(f"   ├── [1. QUICK SELL (Bulk/Liquidity)]: {format_gems(fast_price)}")
        print(f"   ├── [2. STANDARD MARKET PRICE (Booth)]: {format_gems(std_price)}")
        print(f"   └── [3. MAXIMUM SELL (Profit / Patience)]: {format_gems(max_price)}")
    else:
        print("   └── Insufficient data to suggest prices.")
        
    print("==========================================================================")
    return True

def run_analysis():
    global APP_CACHE

    while True:
        clear_screen()
        print("==========================================================================")
        print("                       🏆 NAVIGATION CENTER 🏆                           ")
        print("==========================================================================")
        print("  Select a numeric option:\n")
        print("  [1] 🔍 Search Any Item (Dynamic Search)")
        print("  [2] 🕒 Query History (Summary of Searched Items)")
        print("  " + "-" * 68)
        print("  [0] Exit Program")
        print("==========================================================================")
        
        option = input("👉 Enter your option: ").strip()

        if option == "0":
            print("\nExiting the application safely. See you soon!")
            break
            
        elif option == "1":
            clear_screen()
            print("==========================================================================")
            print("                       🔍 DYNAMIC ITEM SEARCH                              ")
            print("==========================================================================")
            query = input("\n👉 Enter the name of the item you want to search: ").strip().lower()

            if not query:
                continue

            if APP_CACHE["items_data"] is None:
                print("\n⏳ Synchronizing complete API database...")
                APP_CACHE["items_data"] = fetch_ps99rap_data()
                if not APP_CACHE["items_data"]:
                    input("\n❌ Error fetching database. Press ENTER to return.")
                    continue

            results = []
            for slug, info in APP_CACHE["items_data"].items():
                name = info.get("name", "")
                cat = info.get("category", "")
                if query in name.lower():
                    results.append((slug, name, cat))

            if not results:
                print(f"\n❌ No item found containing '{query}'.")
                input("\nPress ENTER to return to the menu.")
                continue

            print(f"\n✅ {len(results)} item(s) found. Showing the first 15:")
            for i, (slug, name, cat) in enumerate(results[:15]):
                print(f"  [{i}] {name} (Category: {cat})")

            choice = input("\n👉 Enter the item number to analyze (or ENTER to cancel): ").strip()

            if choice.isdigit() and int(choice) < len(results[:15]):
                idx = int(choice)
                selected_slug, selected_name, selected_cat = results[idx]

                print(f"\n⏳ Loading data for '{selected_name}'...")
                
                if selected_name in ITEM_BLUEPRINTS:
                    deps = get_blueprint_dependencies(selected_name)
                    success_deps, item_to_slug_deps = ensure_item_data_loaded(deps)
                else:
                    success_deps, item_to_slug_deps = ensure_item_data_loaded([(selected_cat, selected_name)])

                if not success_deps:
                    print("\n❌ Error obtaining item data.")
                    input("Press ENTER to return.")
                    continue

                display_success = display_item_details(selected_name, selected_cat, selected_slug)

                if display_success:
                    hist_item = (selected_name, selected_cat, selected_slug)
                    if hist_item not in APP_CACHE["searched_items"]:
                        APP_CACHE["searched_items"].append(hist_item)

                input("\nPress ENTER to return to the main menu.")
            
        elif option == "2":
            while True:
                clear_screen()
                print("==========================================================================")
                print("               🕒 SESSION QUERY HISTORY                                   ")
                print("==========================================================================")
                
                searched = APP_CACHE.get("searched_items", [])
                if not searched:
                    print("\n  No items searched in this session yet!")
                    print("  Go to option [1] to search and analyze some items first.\n")
                    print("==========================================================================")
                    input("Press ENTER to return to the menu.")
                    break
                    
                print(f" {'Index':<8} | {'Item':<22} | {'Current RAP':<11} | {'30D Median':<11} | {'Decision':<15}")
                print("-" * 80)
                
                for idx, (name, cat, slug) in enumerate(searched):
                    if slug in APP_CACHE["stats"]:
                        st = APP_CACHE["stats"][slug]
                        stable_price = st.get("stable_price")
                        current_rap = st.get("current_rap")
                        
                        if stable_price is None or current_rap is None:
                            print(f"  [{idx:<4}] | {name:<20} | {'ERROR':<11} | {'ERROR':<11} | [EXPIRED DATA]")
                            continue
                        
                        if name in ITEM_BLUEPRINTS:
                            analysis = calculate_dynamic_blueprint(name)
                            if not analysis:
                                print(f"  [{idx:<4}] | {name:<20} | {format_gems(current_rap):<11} | {format_gems(stable_price):<11} | [DEP. ERROR]")
                                continue
                            ev_val = analysis["ev"]
                            item_type = analysis["type"]
                            if item_type == "tool":
                                decision = "RESERVE"
                            else:
                                decision = "SELL" if stable_price > ev_val else "USE"
                        else:
                            if stable_price > 0 and current_rap > 1.30 * stable_price:
                                decision = "SELL (MANIP.)"
                            elif stable_price > 0 and current_rap < 0.70 * stable_price:
                                decision = "BUY (FLIP)"
                            else:
                                decision = "STABLE / KEEP"
                                
                        print(f"  [{idx:<4}] | {name:<20} | {format_gems(current_rap):<11} | {format_gems(stable_price):<11} | [{decision}]")
                        
                print("==========================================================================")
                print("  💡 Enter the index number to review the Spec Sheet instantly (direct cache).")
                choice = input("👉 Enter the index number (or ENTER to return to the menu): ").strip()
                
                if not_choice := not choice:
                    break
                    
                if choice.isdigit() and int(choice) < len(searched):
                    selected_idx = int(choice)
                    name_choice, cat_choice, slug_choice = searched[selected_idx]
                    
                    display_item_details(name_choice, cat_choice, slug_choice)
                    input("\nPress ENTER to return to history.")
                else:
                    print("\n❌ Invalid index! Please try again.")
                    time.sleep(1)
            
        else:
            print("\n❌ Invalid option! Choose a valid number from the menu.")
            time.sleep(1.5)

if __name__ == "__main__":
    try:
        main_app = run_analysis
        main_app()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by the user. Exiting safely...")
