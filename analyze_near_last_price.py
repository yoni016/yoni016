#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ניתוח 7 ההוראות הקרובות ביותר למחיר האחרון
"""

import time
import ccxt

# -------- CONFIG -------- #
PAIR = 'LTC/NIS'         # זוג המטבע
NUM_ORDERS = 7           # כמה הוראות לבדוק מכל צד
INTERVAL_SEC = 1         # שניות בין בדיקות
RUN_TIME_SEC = 30        # זמן ריצה כולל
# ------------------------ #

ex = ccxt.bit2c({'enableRateLimit': True})


def get_nearest_orders(order_book, last_price, side, count=7):
    """מחזיר את count ההוראות הקרובות ביותר למחיר האחרון"""
    orders = order_book['asks'] if side == 'ask' else 'bids']
    
    if side == 'ask':
        # עבור asks - רוצים את המחירים הנמוכים ביותר (קרובים ללast)
        return sorted(orders, key=lambda x: x[0])[:count]
    else:
        # עבור bids - רוצים את המחירים הגבוהים ביותר (קרובים ללast)
        return sorted(orders, key=lambda x: x[0], reverse=True)[:count]


def main():
    print(f"\n=== ניתוח {NUM_ORDERS} הוראות קרובות למחיר האחרון ===")
    print(f"PAIR: {PAIR}")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < RUN_TIME_SEC:
            # קבל מידע על המטבע
            ticker = ex.fetch_ticker(PAIR)
            last_price = ticker['last']
            
            # קבל את ספר הפקודות
            order_book = ex.fetch_order_book(PAIR)
            
            print(f"\n--- מחיר אחרון: {last_price:.2f} ₪ ---")
            print(f"זמן: {ticker['datetime']}")
            
            # נתח את הצד של המוכרים (asks)
            print(f"\n{NUM_ORDERS} המוכרים הקרובים ביותר:")
            nearest_asks = get_nearest_orders(order_book, last_price, 'ask', NUM_ORDERS)
            
            ask_prices = []
            for i, (price, amount) in enumerate(nearest_asks):
                value = price * amount
                distance = price - last_price
                print(f"  [{i+1}] מחיר: {price:.2f} ₪ | כמות: {amount:.6f} | שווי: {value:.2f} ₪ | מרחק: +{distance:.2f} ₪")
                ask_prices.append(price)
            
            if ask_prices:
                print(f"\n  מוכרים - מינימום: {min(ask_prices):.2f} ₪ | מקסימום: {max(ask_prices):.2f} ₪")
            
            # נתח את הצד של הקונים (bids)
            print(f"\n{NUM_ORDERS} הקונים הקרובים ביותר:")
            nearest_bids = get_nearest_orders(order_book, last_price, 'bid', NUM_ORDERS)
            
            bid_prices = []
            for i, (price, amount) in enumerate(nearest_bids):
                value = price * amount
                distance = last_price - price
                print(f"  [{i+1}] מחיר: {price:.2f} ₪ | כמות: {amount:.6f} | שווי: {value:.2f} ₪ | מרחק: -{distance:.2f} ₪")
                bid_prices.append(price)
            
            if bid_prices:
                print(f"\n  קונים - מינימום: {min(bid_prices):.2f} ₪ | מקסימום: {max(bid_prices):.2f} ₪")
            
            # סיכום כללי
            all_prices = ask_prices + bid_prices
            if all_prices:
                print(f"\n=== סיכום כל {len(all_prices)} ההוראות ===")
                print(f"מחיר מינימלי: {min(all_prices):.2f} ₪")
                print(f"מחיר מקסימלי: {max(all_prices):.2f} ₪")
                print(f"טווח: {max(all_prices) - min(all_prices):.2f} ₪")
                print(f"ממוצע: {sum(all_prices) / len(all_prices):.2f} ₪")
            
            print("\n" + "=" * 50)
            time.sleep(INTERVAL_SEC)
            
    except KeyboardInterrupt:
        print("\n\nהופסק על ידי המשתמש (Ctrl+C)")
    except Exception as e:
        print(f"\nשגיאה: {e}")


if __name__ == "__main__":
    main()