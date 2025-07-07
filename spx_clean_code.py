"""
SPX Iron‑Condor bot – Tradier sandbox (paper) account
----------------------------------------------------
• פותח איירון‑קונדו מיד עם הפעלת הקוד
• גידור דלתא במניות SPY לפי רמות Δ 0.70 → 0.85 → 1.00 (עד 100 מניות)
• סגירה אוטומטית ברווח ≥ 75 % או הפסד ≥ 90 % מהקרדיט הראשוני
• Fail‑Safe: סגירה גורפת ב‑15:40 ET
• יומן עסקאות נשמר בזיכרון בלבד (trade_log)

‒ נכתב עבור חשבון הסאנדבוקס של Tradier – החלף TOKEN ו‑ACCOUNT_ID לחשבון Live.
"""

from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ───────────────────────── CONFIG ─────────────────────────
ACCOUNT_ID = "VA59151108"           # sandbox
TOKEN      = "MeZYc0JGI4iFdTeGUA4mv6JsTAYd"  # sandbox
BASE_URL   = "https://sandbox.tradier.com/v1"
HEADERS    = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

UNDERLYING       = "SPX"
HEDGE_SYMBOL     = "SPY"  # נגדר SPY כי SPX הוא אינדקס שלא ניתן לקנות ישירות
CONTRACT_SIZE    = 100
HEDGE_LEVELS     = [0.70, 0.85, 1.00]
BUFFER_PCT       = 0.001          # 0.1 %
TAKE_PROFIT_PCT  = 0.75           # 75 %
STOP_LOSS_PCT    = 0.90           # 90 %
MAX_HEDGE_SHARES = 100
FAILSAFE_ET      = (15, 40)       # 15:40 ET

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")

try:
    ET = ZoneInfo("America/New_York")
except ZoneInfoNotFoundError:
    import datetime as _dt, warnings
    warnings.warn("tzdata missing – falling back to UTC")
    ET = _dt.timezone.utc

# ───────────────────────── MODELS ─────────────────────────
@dataclass
class Trade:
    symbol: str
    side: str          # BUY / SELL
    qty: int
    price: float
    asset_type: str    # option / stock
    option_symbol: Optional[str] = None
    expiration: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

trade_log: List[Trade] = []

# ──────────────────────── API helpers ─────────────────────

def _get(url: str, params: Dict | None = None):
    r = requests.get(url, headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r.json()

def _post(url: str, data: Dict):
    r = requests.post(url, headers=HEADERS, data=data)
    if not r.ok:
        logging.error("HTTP %d: %s", r.status_code, r.text)
    r.raise_for_status()
    return r.json()

def market_clock() -> Dict:
    """Get market clock, handle potential None or malformed responses."""
    try:
        response = _get(f"{BASE_URL}/markets/clock")
        if response and "clock" in response and response["clock"]:
            return response["clock"]
        else:
            logging.warning("Market clock returned empty response, assuming market is open")
            return {"state": "open", "next_change": None}
    except Exception as e:
        logging.error("Failed to get market clock: %s", e)
        return {"state": "open", "next_change": None}

def option_expirations(symbol: str) -> List[str]:
    """Get available expiration dates for the given symbol."""
    return _get(f"{BASE_URL}/markets/options/expirations", {"symbol": symbol})["expirations"]["date"]

def latest_quote(symbol: str, greeks: bool = False) -> Dict:
    return _get(
        f"{BASE_URL}/markets/quotes",
        {"symbols": symbol, "greeks": str(greeks).lower()},
    )["quotes"]["quote"]

def option_chain(symbol: str, expiration: str) -> List[Dict]:
    """Get option chain for symbol and expiration. Handles null response."""
    try:
        response = _get(
            f"{BASE_URL}/markets/options/chains",
            {"symbol": symbol, "expiration": expiration, "greeks": "true"},
        )
        options = response.get("options")
        if options is None or options.get("option") is None:
            raise ValueError(f"No options available for {symbol} expiration {expiration}")
        return options["option"]
    except Exception as e:
        logging.error("Failed to get option chain: %s", e)
        raise

def place_order(symbol: str, qty: int, side: str,
                op_class: str = "equity", option_symbol: str | None = None):
    body = {
        "class": op_class,
        "symbol": option_symbol or symbol,
        "side": side.lower(),
        "quantity": qty,
        "type": "market",
        "duration": "day",
    }
    logging.info("Placing %s %d %s", side.upper(), qty, option_symbol or symbol)
    return _post(f"{BASE_URL}/accounts/{ACCOUNT_ID}/orders", body)

# ─────────────────────── UTILS ────────────────────────────
ET_now = lambda: datetime.now(tz=ET)

def wait_until(dt_target: datetime):
    while ET_now() < dt_target:
        time.sleep(1)

def nearest_strike(price: float) -> int:
    """Round to the closest strike (SPX strikes are usually in 5s or 10s)."""
    # For SPX, round to nearest 5 or 10 depending on price level
    if price < 1000:
        step = 5
    elif price < 3000:
        step = 5
    else:
        step = 5
    
    return round(price / step) * step

def nearest_expiration() -> str:
    """Get the nearest expiration date (>= today)."""
    today = ET_now().date()
    expirations = option_expirations(UNDERLYING)
    
    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        if exp_date >= today:
            return exp_str
    
    raise ValueError("No suitable expiration found")

def make_symbol(option_type: str, strike: int, expiration: str) -> str:
    """Build SPX option symbol: SPX YYMMDD C/P strike×1000."""
    exp_formatted = expiration.replace('-', '')[2:]  # YYMMDD
    strike_formatted = f"{strike * 1000:07d}"  # 7 digits for SPX (higher strikes)
    return f"{UNDERLYING}{exp_formatted}{option_type.upper()}{strike_formatted}"

# ─────────────── BUILD & OPEN IRON CONDOR ────────────────

def build_iron_condor(today: str) -> Dict:
    try:
        chain = option_chain(UNDERLYING, today)
    except ValueError:
        # If daily expiry doesn't exist, try nearest available
        logging.warning("Daily expiry not available, using nearest expiration")
        today = nearest_expiration()
        chain = option_chain(UNDERLYING, today)
    
    spot  = latest_quote(UNDERLYING)["last"]
    atm   = nearest_strike(spot)

    call_atm = next((c for c in chain if c["strike"] == atm and c["option_type"] == "call"), None)
    put_atm  = next((p for p in chain if p["strike"] == atm and p["option_type"] == "put"), None)
    
    if not call_atm or not put_atm:
        # If exact ATM not found, find closest
        call_atm = min([c for c in chain if c["option_type"] == "call"], 
                      key=lambda x: abs(x["strike"] - atm))
        put_atm = min([p for p in chain if p["option_type"] == "put"], 
                     key=lambda x: abs(x["strike"] - atm))
    
    prem = (float(call_atm["ask"]) + float(put_atm["bid"])) / 2

    sc, sp = round(atm + prem), round(atm - prem)   # short call / put
    lc, lp = sc + 25, sp - 25                       # long call / put (wider for SPX)
    logging.info("Strikes SC %d SP %d LC %d LP %d | credit≈%.2f", sc, sp, lc, lp, prem*2)

    # Build option symbols using the corrected format
    legs = [
        (make_symbol("C", sc, today), "sell"),
        (make_symbol("P", sp, today), "sell"),
        (make_symbol("C", lc, today), "buy"),
        (make_symbol("P", lp, today), "buy")
    ]
    
    for sym, side in legs:
        place_order(UNDERLYING, 1, side, "option", sym)
        trade_log.append(Trade(UNDERLYING, side.upper(), 1, 0.0, "option", sym, today))

    credit = prem*2
    return {
        "credit": credit,
        "upper_be": sc + credit,
        "lower_be": sp - credit,
    }

# ──────────────────── P/L & DELTA ─────────────────────────

def update_quotes(symbols: List[str]) -> Dict[str, Dict]:
    joined = ",".join(symbols)
    qdata = _get(f"{BASE_URL}/markets/quotes", {"symbols": joined, "greeks": "true"})["quotes"]["quote"]
    lst = qdata if isinstance(qdata, list) else [qdata]
    return {q["symbol"]: q for q in lst}

def total_delta(quotes: Dict[str, Dict]) -> float:
    d = 0.0
    for t in trade_log:
        if t.asset_type != "option":
            continue
        if t.option_symbol not in quotes:
            continue
        g = quotes[t.option_symbol].get("greeks")
        if not g or g.get("delta") is None:
            continue
        delta = float(g["delta"])
        d += delta if t.side == "BUY" else -delta
    return d

def shares_qty() -> int:
    return sum(t.qty if t.side == "BUY" else -t.qty for t in trade_log if t.asset_type == "stock")

def hedge_to(target_delta: float, quotes: Dict[str, Dict]):
    need = int(round(target_delta * CONTRACT_SIZE)) - shares_qty()
    if need == 0:
        return
    need = max(-MAX_HEDGE_SHARES, min(MAX_HEDGE_SHARES, need))
    side = "buy" if need > 0 else "sell"
    place_order(HEDGE_SYMBOL, abs(need), side)  # Use SPY for hedging
    trade_log.append(Trade(HEDGE_SYMBOL, side.upper(), abs(need), quotes[HEDGE_SYMBOL]["last"], "stock"))
    logging.info("Δ_now %.2f → hedge %s %d shares", total_delta(quotes), side.upper(), abs(need))

def calc_pl(quotes: Dict[str, Dict], credit: float) -> float:
    pl = 0.0
    for t in trade_log:
        if t.asset_type == "option":
            if t.option_symbol not in quotes:
                continue
            q = quotes[t.option_symbol]
            mkt = float(q["ask"] if t.side == "SELL" else q["bid"])
            pl += (t.price - mkt if t.side == "SELL" else mkt - t.price) * CONTRACT_SIZE
        else:
            if t.symbol not in quotes:
                continue
            mkt = quotes[t.symbol]["last"]
            pl += (mkt - t.price if t.side == "BUY" else t.price - mkt)
    return pl / credit if credit else 0.0

def close_all_positions():
    logging.warning("Closing ALL positions…")
    for t in list(trade_log):
        rev_side = "sell" if t.side == "BUY" else "buy"
        if t.asset_type == "option":
            place_order(UNDERLYING, t.qty, rev_side, "option", t.option_symbol)
        else:
            place_order(t.symbol, t.qty, rev_side)
        trade_log.remove(t)

# ─────────────────────── MAIN LOOP ───────────────────────

def main():
    logging.info("Starting SPX Iron Condor bot - opening position immediately")
    
    today = ET_now().date().isoformat()
    ctx = build_iron_condor(today)
    up_BE, dn_BE, credit = ctx["upper_be"], ctx["lower_be"], ctx["credit"]
    buf_up, buf_dn = up_BE * (1 + BUFFER_PCT), dn_BE * (1 - BUFFER_PCT)
    logging.info("Upper BE %.2f / Lower BE %.2f | buffers %.2f / %.2f", up_BE, dn_BE, buf_up, buf_dn)

    while True:
        now = ET_now()
        if (now.hour, now.minute) >= FAILSAFE_ET:
            logging.info("Fail‑Safe time")
            close_all_positions()
            break

        # Include both SPX and SPY in quotes
        syms = {UNDERLYING, HEDGE_SYMBOL}.union({t.option_symbol for t in trade_log if t.asset_type == "option"})
        quotes = update_quotes(list(syms))
        spot = quotes[UNDERLYING]["last"]
        delta = total_delta(quotes)

        if spot >= buf_up and abs(delta) < HEDGE_LEVELS[-1]:
            for lvl in HEDGE_LEVELS:
                if delta < lvl:
                    hedge_to(lvl, quotes)
                    break
        elif spot <= buf_dn and abs(delta) < HEDGE_LEVELS[-1]:
            for lvl in HEDGE_LEVELS:
                if delta > -lvl:
                    hedge_to(-lvl, quotes)
                    break
        elif dn_BE <= spot <= up_BE and shares_qty() != 0:
            hedge_to(0.0, quotes)

        pl_frac = calc_pl(quotes, credit)
        if pl_frac >= TAKE_PROFIT_PCT:
            logging.info("Take‑Profit %.0f %%", pl_frac*100)
            close_all_positions()
            break
        if pl_frac <= -STOP_LOSS_PCT:
            logging.warning("Stop‑Loss %.0f %%", -pl_frac*100)
            close_all_positions()
            break

        time.sleep(4)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        close_all_positions()
        logging.warning("Interrupted – positions closed")