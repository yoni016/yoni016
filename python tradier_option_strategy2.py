"""
QQQM Iron‑Condor bot – Tradier sandbox (paper) account
----------------------------------------------------
• פותח איירון‑קונדו יומי 3 דקות לאחר פתיחת השוק (09:33 ET)
• גידור דלתא במניות QQQM לפי רמות Δ 0.70 → 0.85 → 1.00 (עד 100 מניות)
• סגירה אוטומטית ברווח ≥ 75 % או הפסד ≥ 90 % מהקרדיט הראשוני
• Fail‑Safe: סגירה גורפת ב‑15:40 ET
• יומן עסקאות נשמר בזיכרון בלבד (trade_log)

‒ נכתב עבור חשבון הסאנדבוקס של Tradier – החלף TOKEN ו‑ACCOUNT_ID לחשבון Live.
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

UNDERLYING       = "QQQM"
CONTRACT_SIZE    = 100
HEDGE_LEVELS     = [0.70, 0.85, 1.00]
BUFFER_PCT       = 0.001          # 0.1 %
TAKE_PROFIT_PCT  = 0.75           # 75 %
STOP_LOSS_PCT    = 0.90           # 90 %
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
    r.raise_for_status()
    return r.json()

def market_clock() -> Dict:
    return _get(f"{BASE_URL}/markets/clock")["clock"]

def latest_quote(symbol: str, greeks: bool = False) -> Dict:
    return _get(
        f"{BASE_URL}/markets/quotes",
        {"symbols": symbol, "greeks": str(greeks).lower()},
    )["quotes"]["quote"]

def option_chain(symbol: str, expiration: str) -> List[Dict]:
    return _get(
        f"{BASE_URL}/markets/options/chains",
        {"symbol": symbol, "expiration": expiration, "greeks": "true"},
    )["options"]["option"]

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
    lower, upper = int(price), int(price) + 1
    return lower if abs(price - lower) < abs(price - upper) else upper

# ─────────────── BUILD & OPEN IRON CONDOR ────────────────

def build_iron_condor(today: str) -> Dict:
    chain = option_chain(UNDERLYING, today)
    spot  = latest_quote(UNDERLYING)["last"]
    atm   = nearest_strike(spot)

    call_atm = next(c for c in chain if c["strike"] == atm and c["option_type"] == "call")
    put_atm  = next(p for p in chain if p["strike"] == atm and p["option_type"] == "put")
    prem = (float(call_atm["ask"]) + float(put_atm["bid"])) / 2

    sc, sp = round(atm + prem), round(atm - prem)   # short call / put
    lc, lp = sc + 7, sp - 7                         # long call / put
    logging.info("Strikes SC %d SP %d LC %d LP %d | credit≈%.2f", sc, sp, lc, lp, prem*2)

    fmt = lambda t, k: f"{UNDERLYING}{today.replace('-', '')[2:]}{t}{k:08d}"
    legs = [(fmt("C", sc*100), "sell"), (fmt("P", sp*100), "sell"),
            (fmt("C", lc*100), "buy"),  (fmt("P", lp*100), "buy")]
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
    place_order(UNDERLYING, abs(need), side)
    trade_log.append(Trade(UNDERLYING, side.upper(), abs(need), quotes[UNDERLYING]["last"], "stock"))
    logging.info("Δ_now %.2f → hedge %s %d shares", total_delta(quotes), side.upper(), abs(need))

def calc_pl(quotes: Dict[str, Dict], credit: float) -> float:
    pl = 0.0
    for t in trade_log:
        if t.asset_type == "option":
            q = quotes[t.option_symbol]
            mkt = float(q["ask"] if t.side == "SELL" else q["bid"])
            pl += (t.price - mkt if t.side == "SELL" else mkt - t.price) * CONTRACT_SIZE
        else:
            mkt = quotes[UNDERLYING]["last"]
            pl += (mkt - t.price if t.side == "BUY" else t.price - mkt)
    return pl / credit if credit else 0.0

def close_all_positions():
    logging.warning("Closing ALL positions…")
    for t in list(trade_log):
        rev_side = "sell" if t.side == "BUY" else "buy"
        if t.asset_type == "option":
            place_order(UNDERLYING, t.qty, rev_side, "option", t.option_symbol)
        else:
            place_order(UNDERLYING, t.qty, rev_side)
        trade_log.remove(t)

# ─────────────────────── MAIN LOOP ───────────────────────

def main():
    clock = market_clock()
    if clock["state"] == "open":
        next_open = ET_now()
    else:
        next_open = datetime.fromisoformat(clock["next_change"]).astimezone(ET)

    entry_time = next_open.replace(hour=13, minute=49, second=0, microsecond=0)
    logging.info("Waiting until entry time %s", entry_time.strftime("%H:%M:%S"))
    wait_until(entry_time)

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

        syms = {UNDERLYING}.union({t.option_symbol for t in trade_log if t.asset_type == "option"})
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
