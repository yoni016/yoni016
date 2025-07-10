"""
Debugging version of the Bit2C dominance checker.
Adds verbose output of every order that falls within the configured price and value bands.
"""

import time
import ccxt  # pip install ccxt  # type: ignore

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
    return PRICE_MIN <= price <= PRICE_MAX and in_my_value_band(price, amount)


def best_price(levels, side):
    """ההוראה הטובה ביותר מבין הרשימה הנתונה."""
    return min(levels, key=lambda l: l[0]) if side == 'ask' else max(levels, key=lambda l: l[0])
# ----------------------------------- #


def main():
    total_snapshots = 0
    mine_first_cnt = 0
    start = time.time()

    try:
        while time.time() - start < RUN_TIME_SEC:
            # 1) משיכת ספר-פקודות
            book = ex.fetch_order_book(PAIR)
            levels = book['asks' if SIDE == 'ask' else 'bids']

            # 2) סינון למשמעותיות (מחיר ∈ [PRICE_MIN,PRICE_MAX] וגם value ∈ [MY_MIN,MY_MAX])
            significant = [lvl for lvl in levels if is_significant(lvl)]

            if significant:                         # יש לפחות הוראה משמעותית אחת
                # ----- DEBUG OUTPUT ----- #
                print("Significant orders (price, amount, value):")
                for idx, (p, a) in enumerate(significant, 1):
                    value = p * a
                    print(f"  {idx:2d}) price={p:,.2f}₪ | amount={a:.8f} | value={value:,.2f}₪")
                # ------------------------ #

                best_sig = best_price(significant, SIDE)

                total_snapshots += 1
                if in_my_value_band(*best_sig):     # ההוראה הטובה ביותר היא שלי
                    mine_first_cnt += 1

                ratio = mine_first_cnt / total_snapshots
                print(f"{total_snapshots:5d} | sig={len(significant):3d} | "
                      f"mine first={mine_first_cnt:4d} | ratio={ratio:.2%}",
                      flush=True)
            else:
                # אין כלל הוראות רלוונטיות בסנאפ-שׁוֹט הזה
                print("No significant orders in this snapshot", flush=True)

            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        # עצירה ידנית – Ctrl+C
        pass

    finally:
        print("\n--- SUMMARY ---")
        print(f"Total snapshots   : {total_snapshots}")
        print(f"My-first snapshots: {mine_first_cnt}")
        dominance = mine_first_cnt / total_snapshots if total_snapshots else 0
        print(f"Dominance ratio   : {dominance:.2%}")


if __name__ == "__main__":
    main()