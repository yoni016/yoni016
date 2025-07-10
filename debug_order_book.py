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

# דגל דיבאג
DEBUG = True
# ------------------------ #

ex = ccxt.bit2c({'enableRateLimit': True})


# ---------- פונקציות עזר ---------- #
def in_my_value_band(price: float, amount: float) -> bool:
    """האם price × amount בטווח-השווי של הבוט שלי?"""
    value = price * amount
    result = MY_MIN <= value <= MY_MAX
    if DEBUG:
        print(f"  [DEBUG] in_my_value_band: price={price:.2f}, amount={amount:.8f}, "
              f"value={value:.2f}, in_band={result}")
    return result


def is_significant(level) -> bool:
    """האם ההוראה גם בטווח-המחיר וגם בטווח-השווי שלי?"""
    price, amount = level
    price_in_range = PRICE_MIN <= price <= PRICE_MAX
    value_in_range = in_my_value_band(price, amount)
    result = price_in_range and value_in_range
    
    if DEBUG and result:  # הדפס רק אם עובר את הסינון
        print(f"  [DEBUG] SIGNIFICANT: price={price:.2f} (in [{PRICE_MIN}, {PRICE_MAX}]), "
              f"amount={amount:.8f}, value={price*amount:.2f}")
    
    return result


def best_price(levels, side):
    """ההוראה הטובה ביותר מבין הרשימה הנתונה."""
    return min(levels, key=lambda l: l[0]) if side == 'ask' else max(levels, key=lambda l: l[0])
# ----------------------------------- #


def main():
    total_snapshots = 0
    mine_first_cnt = 0
    start = time.time()

    print(f"\n=== CONFIG ===")
    print(f"SIDE: {SIDE}")
    print(f"PAIR: {PAIR}")
    print(f"MY VALUE RANGE: {MY_MIN} - {MY_MAX} ₪")
    print(f"PRICE RANGE: {PRICE_MIN} - {PRICE_MAX} ₪")
    print(f"==============\n")

    try:
        while time.time() - start < RUN_TIME_SEC:
            print(f"\n--- Snapshot #{total_snapshots + 1} ---")
            
            # 1) משיכת ספר-פקודות
            book = ex.fetch_order_book(PAIR)
            levels = book['asks' if SIDE == 'ask' else 'bids']
            
            print(f"Total {SIDE}s in order book: {len(levels)}")
            
            # הדפס את 5 ההוראות הראשונות לדוגמה
            if DEBUG and len(levels) > 0:
                print(f"\nFirst 5 {SIDE}s:")
                for i, (price, amount) in enumerate(levels[:5]):
                    value = price * amount
                    print(f"  [{i}] Price: {price:.2f} ₪, Amount: {amount:.8f}, Value: {value:.2f} ₪")

            # 2) סינון למשמעותיות (מחיר ∈ [PRICE_MIN,PRICE_MAX] וגם value ∈ [MY_MIN,MY_MAX])
            print(f"\nChecking for significant orders...")
            significant = [lvl for lvl in levels if is_significant(lvl)]

            if significant:                         # יש לפחות הוראה משמעותית אחת
                print(f"\nFound {len(significant)} significant orders:")
                for i, (price, amount) in enumerate(significant[:10]):  # הדפס עד 10
                    value = price * amount
                    print(f"  [{i}] Price: {price:.2f} ₪, Amount: {amount:.8f}, Value: {value:.2f} ₪")
                
                best_sig = best_price(significant, SIDE)
                print(f"\nBest significant order: Price={best_sig[0]:.2f}, "
                      f"Amount={best_sig[1]:.8f}, Value={best_sig[0]*best_sig[1]:.2f}")

                total_snapshots += 1
                if in_my_value_band(*best_sig):     # ההוראה הטובה ביותר היא שלי
                    mine_first_cnt += 1
                    print(">>> THIS IS MY ORDER! <<<")

                ratio = mine_first_cnt / total_snapshots
                print(f"\nSTATS: {total_snapshots:5d} | sig={len(significant):3d} | "
                      f"mine first={mine_first_cnt:4d} | ratio={ratio:.2%}")
            else:
                # אין כלל הוראות רלוונטיות בסנאפ-שׁוֹט הזה
                print("No significant orders in this snapshot")

            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        # עצירה ידנית – Ctrl+C
        print("\n\nStopped by user (Ctrl+C)")
        pass

    finally:
        print("\n--- SUMMARY ---")
        print(f"Total snapshots   : {total_snapshots}")
        print(f"My-first snapshots: {mine_first_cnt}")
        dominance = mine_first_cnt / total_snapshots if total_snapshots else 0
        print(f"Dominance ratio   : {dominance:.2%}")


if __name__ == "__main__":
    main()