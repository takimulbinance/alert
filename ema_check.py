# ema_check.py
import os, json, requests, pandas as pd
from datetime import datetime

# Load config (from repo)
with open("config.json", "r") as f:
    cfg = json.load(f)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise SystemExit("Set TELEGRAM_TOKEN and CHAT_ID as environment variables (GitHub Secrets).")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

def get_binance_klines(symbol, interval, limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","o","h","l","c","v","close_time","qav","ntrades","tbbav","tbqav","ignore"
    ])
    df["close"] = df["c"].astype(float)
    return df

def check_symbol(symbol):
    try:
        df = get_binance_klines(symbol, cfg.get("interval","5m"), cfg.get("limit",100))
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return

    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()

    # Use last two candles to detect cross
    ema9_now, ema9_prev = df["ema9"].iloc[-1], df["ema9"].iloc[-2]
    ema26_now, ema26_prev = df["ema26"].iloc[-1], df["ema26"].iloc[-2]

    if ema9_now > ema26_now and ema9_prev <= ema26_prev:
        msg = f"🚀 Bullish Cross! 9 EMA crossed ABOVE 26 EMA on {symbol} ({cfg['interval']})\nTime: {datetime.utcfromtimestamp(int(df['close_time'].iloc[-1]/1000)).isoformat()}Z"
        print(msg)
        send_telegram(msg)
    elif ema9_now < ema26_now and ema9_prev >= ema26_prev:
        msg = f"🔻 Bearish Cross! 9 EMA crossed BELOW 26 EMA on {symbol} ({cfg['interval']})\nTime: {datetime.utcfromtimestamp(int(df['close_time'].iloc[-1]/1000)).isoformat()}Z"
        print(msg)
        send_telegram(msg)
    else:
        print(f"{symbol}: No cross. {datetime.utcnow().isoformat()}Z")

def main():
    for s in cfg.get("symbols",[]):
        check_symbol(s)

if __name__ == "__main__":
    main()
