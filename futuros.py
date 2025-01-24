import requests
import os
import pandas as pd
from datetime import datetime
import json
import time

# General parameters
API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Replace with your real API Key
BASE_URL = "https://api.coinalyze.net/v1/"
SYMBOLS = {
    "perpetuos": "BTCUSDT_PERP.A"
}
TIMEFRAMES = ["1hour", "4hour", "daily"]
OUTPUT_FOLDER = "datos_futuros"

# Create output folder
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Candles per timeframe
CANDLES = 2000
TIMEFRAME_SECONDS = {
    "1hour": 3600,
    "4hour": 14400,
    "daily": 86400
}

def calculate_timeframe_range(timeframe, candles):
    now = int(time.time())
    from_timestamp = now - (candles * TIMEFRAME_SECONDS[timeframe])
    return from_timestamp, now

def fetch_data(endpoint, symbols, interval, from_timestamp, to_timestamp, convert_to_usd="false", max_retries=3):
    params = {
        "api_key": API_KEY,
        "symbols": symbols,
        "interval": interval,
        "from": from_timestamp,
        "to": to_timestamp,
        "convert_to_usd": convert_to_usd
    }
    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}?{requests.compat.urlencode(params)}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(f"Successful response for {endpoint} on attempt {attempt + 1}")
            print(f"Data received: {json.dumps(data, indent=2)[:500]}...")  # Print first 500 characters of the response
            return data
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    print(f"Failed after {max_retries} retries for {url}.")
    return None

def process_data(timeframe):
    from_timestamp, to_timestamp = calculate_timeframe_range(timeframe, CANDLES)
    all_data = {}

    data_types = {
        "ohlcv": {"endpoint": "ohlcv-history", "renames": {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "bv": "buy_volume"}},
        "open_interest": {"endpoint": "open-interest-history", "renames": {"t": "timestamp", "o": "oi_open", "h": "oi_high", "l": "oi_low", "c": "oi_close"}},
        "long_short_ratio": {"endpoint": "long-short-ratio-history", "renames": {"t": "timestamp", "r": "long_short_ratio", "l": "longs_percentage", "s": "shorts_percentage"}},
        "liquidation": {"endpoint": "liquidation-history", "renames": {"t": "timestamp", "l": "liquidation_longs", "s": "liquidation_shorts"}},
        "funding_rate": {"endpoint": "funding-rate-history", "renames": {"t": "timestamp", "o": "fr_open", "h": "fr_high", "l": "fr_low", "c": "fr_close"}}
    }

    for data_type, details in data_types.items():
        print(f"Fetching {data_type} for {timeframe}...")
        data = fetch_data(details["endpoint"], SYMBOLS["perpetuos"], timeframe, from_timestamp, to_timestamp)

        if data and isinstance(data, dict) and "history" in data:
            for item in data["history"]:
                try:
                    timestamp = item["t"]
                    if timestamp not in all_data:
                        all_data[timestamp] = {
                            "fecha_hora": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                            "temporalidad": timeframe
                        }
                    for key, new_key in details["renames"].items():
                        if key in item:
                            all_data[timestamp][new_key] = item[key]
                except KeyError as e:
                    print(f"Error accessing timestamp in item: {item}. Error: {e}")
        else:
            print(f"No valid data received for {data_type} in {timeframe}")

    if all_data:
        df = pd.DataFrame.from_dict(all_data, orient='index')
        df = df.sort_values(by="fecha_hora")
        
        print(f"Processed data for {timeframe}:")
        print(df.head())
        print(f"Shape of DataFrame: {df.shape}")

        if not df.empty:
            csv_filename = os.path.join(OUTPUT_FOLDER, f"datos_{timeframe}.csv")
            df.to_csv(csv_filename, index=False)
            print(f"Data saved to {csv_filename}")
        else:
            print(f"No data to save for {timeframe}.")
    else:
        print(f"No data processed for {timeframe}.")

# Process data for each timeframe
for timeframe in TIMEFRAMES:
    print(f"Processing {timeframe}...")
    process_data(timeframe)
