#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"בדיקת מקום-ראשון" — גרסה שמחשבת אך ורק על-סמך הוראות
ש-גם מחיר-היחידה שלהן בטווח מוגדר *וגם* השווי הכולל שלהן
(price × amount) נמצא בטווח-השווי שבו הבוט שלך פועל.

• SIDE        – 'ask' או 'bid'
• PAIR        – זוג המטבע (Bit2C משתמש ב-/NIS)
• MY_MIN/MAX  – טווח השווי (₪) שמאפיין את ההוראות שלך
• PRICE_MIN/MAX – טווח-מחיר (₪) שבו התחרות מעניינת אותך
• INTERVAL_SEC – כמה זמן לחכות בין קריאות
• RUN_TIME_SEC – זמן ריצה כולל
"""

import time
import ccxt  # pip install ccxt

# -------- CONFIG -------- #
SIDE = 'bid'        # 'ask'  או  'bid'
PAIR = 'LTC/NIS'    # למשל 'BTC/NIS', 'ETH/NIS' …

# הבוט שלך שולח הוראות בערך 7k-8.5k ₪
MY_MIN = 3      # ₪
MY_MAX = 15      # ₪

# רק הוראות שמחירן בין 320-330 ₪ מעניינות
PRICE_MIN = 0     # ₪
PRICE_MAX = 33000000     # ₪

INTERVAL_SEC = 0.3  # שניות בין סנאפ-שׁוֹטים
RUN_TIME_SEC = 120  # שניות ריצה (Ctrl-C לעצירה מוקדמת)
# ------------------------ #

ex = ccxt.bit2c({'enableRateLimit': True})


# ---------- פונקציות עזר ---------- #
def in_my_value_band(price: float, amount: float) -> bool:
    """האם price × amount בטווח-השווי של הבוט שלי?"""
    value = price * amount
    return MY_MIN <= value <= MY_MAX


def is_significant(level) -> bool:
    """האם ההוראה גם בטווח-המחיר וגם בטווח-השווי שלי?"""
    price, amount = level
    value = price * amount
    
    price_ok = PRICE_MIN <= price <= PRICE_MAX
    value_ok = in_my_value_band(price, amount)
    
    # דיבוג: הדפסה של כל הוראה שנבדקת
    print(f"    🔍 Order: Price={price:.2f}₪, Amount={amount:.6f}, Value={value:.2f}₪")
    print(f"       Price in range [{PRICE_MIN}-{PRICE_MAX}]: {price_ok}")
    print(f"       Value in range [{MY_MIN}-{MY_MAX}]: {value_ok}")
    print(f"       → SIGNIFICANT: {price_ok and value_ok}")
    
    return price_ok and value_ok


def best_price(levels, side):
    """ההוראה הטובה ביותר מבין הרשימה הנתונה."""
    if side == 'ask':
        return min(levels, key=lambda l: l[0])
    else:
        return max(levels, key=lambda l: l[0])
# ----------------------------------- #


def main():
    total_snapshots = 0
    mine_first_cnt = 0
    start = time.time()

    print(f"🚀 Starting monitoring for {PAIR} {SIDE} side")
    print(f"📊 Looking for orders with:")
    print(f"   • Price range: {PRICE_MIN}₪ - {PRICE_MAX}₪")
    print(f"   • Value range: {MY_MIN}₪ - {MY_MAX}₪")
    print("=" * 60)

    try:
        while time.time() - start < RUN_TIME_SEC:
            print(f"\n📸 Snapshot #{total_snapshots + 1}")
            
            # 1) משיכת ספר-פקודות
            book = ex.fetch_order_book(PAIR)
            levels = book['asks' if SIDE == 'ask' else 'bids']

            print(f"📋 Total {SIDE} orders in book: {len(levels)}")
            
            # הדפסת 5 ההוראות הראשונות (לפני סינון)
            print("🔸 First 5 orders in book:")
            for i, (price, amount) in enumerate(levels[:5]):
                value = price * amount
                print(f"   #{i+1}: {price:.2f}₪ × {amount:.6f} = {value:.2f}₪")

            # 2) סינון למשמעותיות (מחיר ∈ [PRICE_MIN,PRICE_MAX] וגם value ∈ [MY_MIN,MY_MAX])
            print("\n🔍 Checking each order for significance...")
            significant = []
            for lvl in levels:
                if is_significant(lvl):
                    significant.append(lvl)

            print(f"\n✅ Found {len(significant)} significant orders:")
            for i, (price, amount) in enumerate(significant):
                value = price * amount
                print(f"   #{i+1}: {price:.2f}₪ × {amount:.6f} = {value:.2f}₪")

            if significant:                         # יש לפחות הוראה משמעותית אחת
                best_sig = best_price(significant, SIDE)
                best_price_val, best_amount_val = best_sig
                best_value = best_price_val * best_amount_val

                print(f"\n🏆 Best significant order: {best_price_val:.2f}₪ × {best_amount_val:.6f} = {best_value:.2f}₪")

                total_snapshots += 1
                if in_my_value_band(*best_sig):     # ההוראה הטובה ביותר היא שלי
                    mine_first_cnt += 1
                    print("✨ This is MY order! (in my value band)")
                else:
                    print("❌ This is NOT my order (outside my value band)")

                ratio = mine_first_cnt / total_snapshots
                print(f"\n📊 Stats: {total_snapshots:5d} | sig={len(significant):3d} | "
                      f"mine first={mine_first_cnt:4d} | ratio={ratio:.2%}")
            else:
                # אין כלל הוראות רלוונטיות בסנאפ-שׁוֹט הזה
                print("❗ No significant orders in this snapshot")

            print("-" * 60)
            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        # עצירה ידנית – Ctrl+C
        print("\n🛑 Interrupted by user")

    finally:
        print("\n" + "=" * 60)
        print("📈 FINAL SUMMARY")
        print("=" * 60)
        print(f"Total snapshots   : {total_snapshots}")
        print(f"My-first snapshots: {mine_first_cnt}")
        dominance = mine_first_cnt / total_snapshots if total_snapshots else 0
        print(f"Dominance ratio   : {dominance:.2%}")


if __name__ == "__main__":
    main()