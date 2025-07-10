#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ניתוח 7 ההוראות מתחת למחיר האחרון
"""

import time
import ccxt

# הגדרות
PAIR = 'LTC/NIS'

# יצירת חיבור
exchange = ccxt.bit2c({'enableRateLimit': True})


def main():
    print(f"מנתח 7 הוראות מתחת למחיר האחרון עבור {PAIR}")
    print("-" * 50)
    
    try:
        # קבל מידע על המטבע
        ticker = exchange.fetch_ticker(PAIR)
        last_price = ticker['last']
        print(f"מחיר אחרון: {last_price:.2f} ₪\n")
        
        # קבל את ספר הפקודות
        order_book = exchange.fetch_order_book(PAIR)
        
        # קח את 7 הוראות הקנייה הגבוהות ביותר (מתחת למחיר האחרון)
        bids = order_book['bids'][:7]
        
        print("7 הוראות הקנייה הגבוהות ביותר:")
        print("מס' | מחיר (₪) | כמות | שווי (₪)")
        print("-" * 50)
        
        prices = []
        for i, (price, amount) in enumerate(bids):
            value = price * amount
            prices.append(price)
            print(f"{i+1:3d} | {price:9.2f} | {amount:9.6f} | {value:10.2f}")
        
        print("-" * 50)
        print(f"\nסיכום:")
        print(f"מחיר מינימלי: {min(prices):.2f} ₪")
        print(f"מחיר מקסימלי: {max(prices):.2f} ₪")
        print(f"טווח מחירים: {max(prices) - min(prices):.2f} ₪")
        print(f"מחיר ממוצע: {sum(prices) / len(prices):.2f} ₪")
        
    except Exception as e:
        print(f"שגיאה: {e}")


if __name__ == "__main__":
    main()