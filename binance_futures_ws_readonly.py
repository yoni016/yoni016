import asyncio, json, requests, websockets, time, os, re, hmac, hashlib, base64
from datetime import datetime, timedelta, timezone


def now_utc():
    return datetime.now(timezone.utc)


# משתנה דיבאג (הוסף אחרי now_utc)
DEBUG = os.getenv("BIT2C_DEBUG", "1") == "1"
NAIVE_TZ_OFFSET_HOURS = float(os.getenv("BIT2C_NAIVE_UTC_OFFSET_HOURS", "0"))


# מפתחות (קריאה בלבד)
BINANCE_API_SECRET = "kEvqwtoDwsFaQMSJTGEQ21CpvVCxkO4HQYAadURt4o2sWSIvZYUmgsV70sM49Wa8"
BINANCE_API_KEY = "WvO6frqqkr9lYBinYfvwyN2eaWya3cYI8Ie04ei3pkgSJWMgwRMVqbzyf0mzSvDn"


FAPI_REST = "https://fapi.binance.com"
FAPI_WS = "wss://fstream.binance.com/ws"


session = requests.Session()
session.headers.update({"X-MBX-APIKEY": BINANCE_API_KEY})


RUN_BINANCE_WS = os.getenv("RUN_BINANCE_WS", "0") == "1"


def get_listen_key():
    r = session.post(f"{FAPI_REST}/fapi/v1/listenKey", timeout=10)
    r.raise_for_status()
    return r.json()["listenKey"]


# קובץ המפתחות המקומי (באותה תיקייה)
NOTE_PATH = os.path.join(os.path.dirname(__file__), "AVG CHECK API.txt")


# טעינת חשבונות מה‑NOTE (פורמט חופשי, לא חייב JSON תקין)
def load_bit2c_accounts(path=NOTE_PATH):
    if not os.path.exists(path):
        return []
    accounts, cur = [], {}
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            m = re.search(r'"AccountName"\s*:\s*"([^"]+)"', ln)
            if m:
                if cur:
                    accounts.append(cur)
                    cur = {}
                cur["AccountName"] = m.group(1).strip()
            m = re.search(r'"Key"\s*:\s*"([^"]+)"', ln)
            if m:
                cur["Key"] = m.group(1).strip()
            m = re.search(r'"Secret"\s*:\s*"([^"]+)"', ln)
            if m:
                cur["Secret"] = m.group(1).strip()
        if cur:
            accounts.append(cur)
    # ניקוי תווים חריגים ב‑Secret (אם יש placeholders)
    for a in accounts:
        if "Secret" in a:
            a["Secret"] = a["Secret"].replace("ס", "")
    return [a for a in accounts if a.get("Key") and a.get("Secret")]


# חתימה וקריאת API פרטי של BIT2C
BIT2C_BASE = "https://bit2c.co.il/"  # ניתן לשנות ל־api הרשמי אם צריך


def _bit2c_sign(secret_upper_ascii, qstring):
    return base64.b64encode(
        hmac.new(secret_upper_ascii.encode("ascii"), qstring.encode("ascii"), hashlib.sha512).digest()
    ).decode()


def bit2c_private(path, params, key, secret, method="GET", timeout=7):
    params = dict(params or {})
    # שימוש ב-nonce גדול יותר
    params["nonce"] = str(int(time.time() * 1000000))  # מיקרושניות במקום מילישניות
    q = "&".join([f"{k}={params[k]}" for k in params])
    sign = _bit2c_sign(secret.upper(), q)
    url = BIT2C_BASE + path
    headers = {"Key": key, "Sign": sign}
    if method.upper() == "GET":
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
    else:
        r = requests.post(url, data=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


# המרת Binance→BIT2C (USDT→NIS)
def to_bit2c_pair(binance_symbol):
    for suf in ("USDT", "USD", "BUSD", "USDC"):
        if binance_symbol.endswith(suf):
            return f"{binance_symbol[:-len(suf)]}NIS"
    return None


# USD→ILS (CurrencyConverterAPI)
def get_usdils_ccapi(api_key="f99c92a284134266b9e4ed27176f20ad", timeout=5):
    r = requests.get(
        "https://api.currconv.com/api/v8/convert",
        params={"q": "USD_ILS", "compact": "ultra", "apiKey": api_key},
        timeout=timeout,
    )
    r.raise_for_status()
    return float(r.json().get("USD_ILS") or 0)


# ---- עזר: נירמול זמנים ממקורות שונים ----
_EPOCH_1970 = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_epoch_number_to_seconds(value_number):
    v = float(value_number)
    # מזהה מיקרו/מילי/שניות לפי סדר גודל
    if v > 1e14:  # microseconds
        return int(v / 1e6)
    if v > 1e12:  # milliseconds
        return int(v / 1e3)
    if v > 1e10:  # seconds with possible extra precision
        return int(v)
    # טיפוסית שניות (10 ספרות)
    return int(v)


def _parse_iso_datetime_to_seconds(value_str):
    s = value_str.strip()
    # .NET style /Date(1693512345000)/
    m = re.match(r"^/Date\((\d{10,17})\)/$", s)
    if m:
        return _parse_epoch_number_to_seconds(int(m.group(1)))

    # Pure digits string
    if re.fullmatch(r"\d{10,17}", s):
        return _parse_epoch_number_to_seconds(int(s))

    # Normalize Zulu to explicit UTC offset for fromisoformat
    s_norm = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s_norm)
    except ValueError:
        # Try common formats
        fmts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S.%f",
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                # נניח UTC אם לא צוין אזור זמן
                dt = dt.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None

    # אם תאריך ללא אזור זמן - נתייחס לפי offset מוגדר, ברירת מחדל UTC
    if dt.tzinfo is None:
        tz = timezone(timedelta(hours=NAIVE_TZ_OFFSET_HOURS)) if NAIVE_TZ_OFFSET_HOURS != 0 else timezone.utc
        dt = dt.replace(tzinfo=tz)
    return int(dt.astimezone(timezone.utc).timestamp())


def _extract_timestamp_seconds(obj):
    if not isinstance(obj, dict):
        return None

    # מקורות אפשריים לשדה זמן בהזמנה/עסקה
    candidate_keys = ("Time", "time", "Created", "created", "Date", "date")
    for key in candidate_keys:
        if key in obj and obj[key] is not None:
            v = obj[key]
            if isinstance(v, (int, float)):
                return _parse_epoch_number_to_seconds(v)
            if isinstance(v, str):
                ts = _parse_iso_datetime_to_seconds(v)
                if ts is not None:
                    return ts

    # אם אין זמן ישירות על ההזמנה, ננסה מהמילויים
    fills = obj.get("Trades") or obj.get("trades") or []
    if isinstance(fills, list) and fills:
        for f in reversed(fills):  # נעדיף את האחרון
            ts = _extract_timestamp_seconds(f)
            if ts is not None:
                return ts
    return None


# שאיבת עסקאות סגורות לחלון זמן (מכל המילויים) לחשבון יחיד
def _try_parse_json(txt):
    try:
        return json.loads(txt)
    except Exception:
        print(f"[BIT2C] Unexpected response: {txt[:180]}...")
        return []


def bit2c_closed_in_window(pair, window_sec, key, secret):
    print(f"🔍 Checking {pair} for last {window_sec} seconds...")
    now = int(time.time())
    tries = []

    # 1) יוניקס שניות
    tries.append({"fromTime": now - max(window_sec, 5) - 120, "toTime": now + 5, "pair": pair})
    # 2) ISO
    to_t = now_utc()
    from_t = to_t - timedelta(seconds=max(window_sec, 5) + 120)
    tries.append({"fromTime": from_t.isoformat(), "toTime": to_t.isoformat(), "pair": pair})
    # 3) בלי from/to
    tries.append({"pair": pair})

    data = []
    for i, p in enumerate(tries):
        try:
            print(f"  Try {i+1}: {p}")
            txt = bit2c_private("Order/OrderHistory", p, key, secret, method="GET")
            print(f"  Response length: {len(txt)} bytes")
            print(f"  Response preview: {txt[:200]}...")
            data = _try_parse_json(txt)
            if data:
                print(f"  ✅ Success with try {i+1}")
                break
        except Exception as e:
            print(f"  ❌ Try {i+1} failed: {e}")

    rows = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
    print(f"  Parsed {len(rows)} rows")

    cutoff = int(time.time()) - window_sec
    out = []

    for it in rows:
        # בדיקה שהאובייקט הוא dict ולא string
        if not isinstance(it, dict):
            continue

        status = str(it.get("Status") or it.get("status") or "").upper()
        if "OPEN" in status or "NEW" in status:
            continue

        # נירמול זמן (תמיכה ב‑epoch שניות/מילי/מיקרו, ISO, .NET /Date(...)/)
        ts = _extract_timestamp_seconds(it)

        if ts is not None and ts < cutoff:
            continue

        qty = float(it.get("Amount") or it.get("amount") or 0)
        avg = float(it.get("AvgPrice") or it.get("avgPrice") or it.get("AverageRate") or 0)
        side = "BUY" if bool(it.get("IsBid") or it.get("isBid") or False) else "SELL"
        fills = it.get("Trades") or it.get("trades") or []
        if (avg <= 0 or qty <= 0) and isinstance(fills, list) and fills:
            sum_q = sum(float(f.get("Amount") or f.get("amount") or 0) for f in fills)
            sum_v = sum(
                float(f.get("Amount") or f.get("amount") or 0) * float(f.get("Price") or f.get("price") or 0)
                for f in fills
            )
            if sum_q > 0:
                qty, avg = sum_q, (sum_v / sum_q)
            side = "BUY" if bool((fills[-1] or {}).get("IsBid") or (fills[-1] or {}).get("isBid") or False) else "SELL"

        if qty > 0 and avg > 0:
            out.append({"side": side, "qty": qty, "avg": avg})

    print(f"  Final result: {len(out)} transactions")
    return out


# בדיקת 4 החשבונות לקונסול קצר
def check_all_accounts(pair, window_sec=5):
    accs = load_bit2c_accounts()
    out = []
    for a in accs:
        try:
            rows = bit2c_closed_in_window(pair, window_sec, a["Key"], a["Secret"])
            if rows:
                # מציג את האחרונה בצמצום
                r = rows[-1]
                out.append(f'{a["AccountName"]} {r["side"]} {r["qty"]:.6f} {pair} AVG {r["avg"]:.2f}')
        except Exception:
            continue
    return out


# ---- עסקאות אחרונות ב‑BIT2C ----
def bit2c_recent_trades(pair, window_sec=60):
    if not pair:
        return []
    s = globals().get("session")
    if s is None:
        s = requests.Session()
    url = f"https://bit2c.co.il/Exchanges/{pair}/trades.json"
    try:
        r = s.get(url, timeout=5)
        r.raise_for_status()
        trades = r.json()
    except Exception:
        return []
    now = int(time.time())
    return [t for t in trades if now - int(t.get("date", 0)) <= window_sec]


async def main():
    print("🚀 Code started running...")
    print("🔌 Listening to Binance...")
    print("⏰ UsdcNis report every 4 hours...")

    # דוח USDCNIS: חלון 4 שעות, כל 4 שעות
    asyncio.create_task(usdc_scheduler(window_hours=4, interval_hours=4))
    # האזנה ל‑Binance + בדיקות 5 שניות ב‑BIT2C כרגיל
    await stream_user_data(window_sec_bit2c=5)


async def usdc_scheduler(window_hours=48, interval_hours=4):  # 48 שעות
    print(f"📊 UsdcNis report: {window_hours}h window, every {interval_hours}h")
    # ריצה מיידית ואז כל interval_hours
    report_usdc_accounts(window_hours)
    while True:
        await asyncio.sleep(int(interval_hours * 3600))
        report_usdc_accounts(window_hours)


def report_usdc_accounts(window_hours=4):
    accs = load_bit2c_accounts()
    print(f"Checking {len(accs)} accounts...")

    try:
        usdils = get_usdils_ccapi()
    except Exception:
        usdils = 0.0
    window_sec = int(window_hours * 3600)

    ts = now_utc().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] UsdcNis report last {window_hours}h")

    any_line = False
    for a in accs:
        print(f"Checking account {a['AccountName']}...")
        rows = bit2c_closed_in_window(USDC_PAIR, window_sec, a["Key"], a["Secret"])
        print(f"  Found {len(rows)} transactions")

        sums = _summarize_side(rows)
        for side in ("BUY", "SELL"):
            s = sums[side]
            if s["asset"] <= 0:
                continue
            diff = _pct_vs_real(s["avg"], usdils, side)
            print(
                f'BIT2C {a["AccountName"]} {side} {s["asset"]:.6f} USDC | NIS={s["nis"]:,.2f} | AVG={s["avg"]:.4f} | USDILS={usdils:.4f} | Δ={diff:+.2f}%'
            )
            any_line = True

    if not any_line:
        print("No UsdcNis transactions in window.")


async def stream_user_data(window_sec_bit2c=5):
    print("🔌 Connecting to Binance WebSocket...")
    lk = get_listen_key()
    url = f"{FAPI_WS}/{lk}"
    print(f"✅ Connected to: {url}")

    async with websockets.connect(url, ping_interval=15, ping_timeout=10) as ws:
        print("🎧 Listening for transactions...")
        async for msg in ws:
            data = json.loads(msg)
            if data.get("e") != "ORDER_TRADE_UPDATE":
                continue
            o = data.get("o", {})
            if o.get("x") != "TRADE":
                continue

            sym = o.get("s")
            side = o.get("S")
            qty = float(o.get("l") or 0)
            avg = float(o.get("ap") or o.get("L") or 0)

            pair = to_bit2c_pair(sym)
            usdils = 0.0
            try:
                usdils = get_usdils_ccapi()
            except Exception:
                pass

            # בדיקת 4 החשבונות ב‑BIT2C (חלון 5ש׳׳ כברירת מחדל)
            acc_lines = check_all_accounts(pair, window_sec=window_sec_bit2c) if pair else []

            # הדפסה מסכמת
            print(f"Binance {sym} {side} qty={qty:.6f} avg={avg:,.2f} | USDILS={usdils:.4f}")
            if pair:
                if acc_lines:
                    for ln in acc_lines:
                        print(f"BIT2C {ln}")
                else:
                    print(
                        f"BIT2C {pair}: No closed transactions in last {window_sec_bit2c}s in all accounts"
                    )


# קבוע לצמד
USDC_PAIR = "UsdcNis"


def _summarize_side(rows):
    sums = {"BUY": {"asset": 0.0, "nis": 0.0, "count": 0}, "SELL": {"asset": 0.0, "nis": 0.0, "count": 0}}
    for r in rows:
        side = "BUY" if r.get("side") == "BUY" else "SELL"
        qty = float(r.get("qty", 0.0))
        avg = float(r.get("avg", 0.0))
        if qty <= 0 or avg <= 0:
            continue
        sums[side]["asset"] += qty
        sums[side]["nis"] += qty * avg
        sums[side]["count"] += 1
    for side in ("BUY", "SELL"):
        s = sums[side]
        s["avg"] = (s["nis"] / s["asset"]) if s["asset"] > 0 else 0.0
    return sums


def _pct_vs_real(avg_price, real_rate, side):
    if real_rate <= 0 or avg_price <= 0:
        return 0.0
    if side == "BUY":
        return (real_rate - avg_price) / real_rate * 100.0
    else:  # SELL
        return (avg_price - real_rate) / real_rate * 100.0


if __name__ == "__main__":
    asyncio.run(main())  # מריץ את ההאזנה לבנינאס + דוח USDC/NIS במקביל

