#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"בדיקת מקום-ראשון" — גרסה שמסננת את ה-OrderBook לפי טווח שווי
ואז בודקת אם ההוראה שלי היא הראשונה (מחיר הטוב ביותר) ברשימה המסוננת.

• SIDE        – 'ask' או 'bid'
• PAIR        – זוג המטבע (Bit2C משתמש ב-/NIS)
• FILTER_MIN/MAX – טווח השווי לסינון ה-OrderBook
• MY_MIN/MAX  – טווח השווי של ההוראות שלי
• INTERVAL_SEC – כמה זמן לחכות בין קריאות
• RUN_TIME_SEC – זמן ריצה כולל
"""

import time
import ccxt  # pip install ccxt

# -------- CONFIG -------- #
SIDE = 'bid'        # 'ask'  או  'bid'
PAIR = 'LTC/NIS'    # למשל 'BTC/NIS', 'ETH/NIS' …

# טווח שווי לסינון כל ההוראות מה-OrderBook
FILTER_MIN = 3      # ₪ - כל הוראה עם שווי מתחת לזה תסונן
FILTER_MAX = 15     # ₪ - כל הוראה עם שווי מעל לזה תסונן

# טווח השווי של ההוראות שלי (הבוט)
MY_MIN = 3          # ₪
MY_MAX = 15         # ₪

INTERVAL_SEC = 0.3  # שניות בין סנאפ-שׁוֹטים
RUN_TIME_SEC = 120  # שניות ריצה (Ctrl-C לעצירה מוקדמת)
# ------------------------ #

ex = ccxt.bit2c({'enableRateLimit': True})


# ---------- פונקציות עזר ---------- #
def get_order_value(price: float, amount: float) -> float:
    """מחשב את השווי של הוראה"""
    return price * amount


def is_in_filter_range(price: float, amount: float) -> bool:
    """האם ההוראה בטווח הסינון הכללי?"""
    value = get_order_value(price, amount)
    return FILTER_MIN <= value <= FILTER_MAX


def is_my_order(price: float, amount: float) -> bool:
    """האם זו הוראה שלי (בטווח השווי שלי)?"""
    value = get_order_value(price, amount)
    return MY_MIN <= value <= MY_MAX


def get_best_price_order(filtered_orders, side):
    """מחזיר את ההוראה עם המחיר הטוב ביותר מהרשימה המסוננת"""
    if not filtered_orders:
        return None
    
    if side == 'ask':
        # עבור ASK - המחיר הנמוך ביותר הוא הטוב ביותר
        return min(filtered_orders, key=lambda order: order[0])
    else:
        # עבור BID - המחיר הגבוה ביותר הוא הטוב ביותר
        return max(filtered_orders, key=lambda order: order[0])
# ----------------------------------- #


def main():
    total_snapshots = 0
    mine_first_cnt = 0
    start = time.time()

    print(f"🚀 Starting monitoring for {PAIR} {SIDE} side")
    print(f"📊 Filter range: {FILTER_MIN}₪ - {FILTER_MAX}₪")
    print(f"🤖 My orders range: {MY_MIN}₪ - {MY_MAX}₪")
    print("=" * 60)

    try:
        while time.time() - start < RUN_TIME_SEC:
            # 1) משיכת ספר-פקודות
            book = ex.fetch_order_book(PAIR)
            levels = book['asks' if SIDE == 'ask' else 'bids']

            print(f"\n📸 Snapshot #{total_snapshots + 1}")
            print(f"📋 Total {SIDE} orders in book: {len(levels)}")

            # 2) סינון ההוראות לפי טווח השווי
            filtered_orders = []
            for price, amount in levels:
                if is_in_filter_range(price, amount):
                    filtered_orders.append((price, amount))

            print(f"🔍 Orders after value filtering: {len(filtered_orders)}")

            if filtered_orders:
                # הדפסת הוראות מסוננות (עד 5 ראשונות)
                print("📋 First 5 filtered orders:")
                for i, (price, amount) in enumerate(filtered_orders[:5]):
                    value = get_order_value(price, amount)
                    is_mine = is_my_order(price, amount)
                    marker = "🤖" if is_mine else "  "
                    print(f"   {marker}#{i+1}: {price:.2f}₪ × {amount:.6f} = {value:.2f}₪")

                # 3) מציאת ההוראה עם המחיר הטוב ביותר ברשימה המסוננת
                best_order = get_best_price_order(filtered_orders, SIDE)
                if best_order is None:
                    print("❗ No valid best order found")
                    continue
                best_price, best_amount = best_order
                best_value = get_order_value(best_price, best_amount)

                print(f"\n🏆 Best order in filtered list:")
                print(f"    Price: {best_price:.2f}₪")
                print(f"    Amount: {best_amount:.6f}")
                print(f"    Value: {best_value:.2f}₪")

                # 4) בדיקה אם ההוראה הטובה ביותר היא שלי
                total_snapshots += 1
                if is_my_order(best_price, best_amount):
                    mine_first_cnt += 1
                    print("✨ This is MY order! I'm FIRST in the filtered list! 🥇")
                else:
                    print("❌ This is NOT my order. Someone else is first.")

                # 5) סטטיסטיקות
                ratio = mine_first_cnt / total_snapshots
                print(f"\n📊 Stats:")
                print(f"    Total snapshots: {total_snapshots}")
                print(f"    Filtered orders: {len(filtered_orders)}")
                print(f"    Times I was first: {mine_first_cnt}")
                print(f"    My dominance ratio: {ratio:.2%}")

            else:
                print("❗ No orders in the specified value range")

            print("-" * 60)
            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")

    finally:
        print("\n" + "=" * 60)
        print("📈 FINAL SUMMARY")
        print("=" * 60)
        print(f"Total snapshots   : {total_snapshots}")
        print(f"My-first snapshots: {mine_first_cnt}")
        dominance = mine_first_cnt / total_snapshots if total_snapshots else 0
        print(f"Dominance ratio   : {dominance:.2%}")
        print(f"Filter range used : {FILTER_MIN}₪ - {FILTER_MAX}₪")
        print(f"My orders range   : {MY_MIN}₪ - {MY_MAX}₪")


if __name__ == "__main__":
    main()