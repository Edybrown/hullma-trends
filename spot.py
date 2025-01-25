import requests
import time
import json
import openpyxl

API_KEY = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Replace with your actual Coinalyze API key
SYMBOL = "BTCUSDT.A"
INTERVALS = ["4hour", "1hour", "daily"]
LIMIT = 2000  # Maximum number of periods to retrieve (may be limited by API)

def get_ohlcv_data(symbol, interval, limit):
    """Fetches OHLCV data for the given symbol and interval."""

    base_url = "https://api.coinalyze.net/v1/ohlcv-history"
    current_timestamp = int(time.time())
    from_timestamp = current_timestamp - (limit - 1) * (
        {
            "4hour": 14400,  # 4 hours in seconds
            "1hour": 3600,   # 1 hour in seconds
            "daily": 86400,  # 1 day in seconds
        }[interval]
    )

    params = {
        "api_key": API_KEY,
        "symbols": symbol,
        "interval": interval,
        "from": from_timestamp,
        "to": current_timestamp,
        "limit": limit,
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict) and "history" in data:
            return data["history"]
        else:
            print(f"Unexpected response structure for symbol {symbol} and interval {interval}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol} ({interval}): {e}")
        return None

def save_to_excel(data, filename):
    """Saves the OHLCV data to an Excel XLSX file."""

    workbook = openpyxl.Workbook()
    sheet = workbook.active

    sheet.cell(row=1, column=1).value = "Timestamp (UNIX)"
    sheet.cell(row=1, column=2).value = "Open"
    sheet.cell(row=1, column=3).value = "High"
    sheet.cell(row=1, column=4).value = "Low"
    sheet.cell(row=1, column=5).value = "Close"
    sheet.cell(row=1, column=6).value = "Volume"

    row_index = 2
    for item in data:
        # Check if data is present to avoid errors
        if item.get("t") is not None:
            sheet.cell(row=row_index, column=1).value = item["t"]
            sheet.cell(row=row_index, column=2).value = item["o"]
            sheet.cell(row=row_index, column=3).value = item["h"]
            sheet.cell(row=row_index, column=4).value = item["l"]
            sheet.cell(row=row_index, column=5).value = item["c"]
            sheet.cell(row=row_index, column=6).value = item["v"]
            row_index += 1

    workbook.save(filename)
    print(f"OHLCV data saved to '{filename}'.")

# Main execution
all_data = {}
for interval in INTERVALS:
    ohlcv_data = get_ohlcv_data(SYMBOL, interval, LIMIT)
    if ohlcv_data:
        all_data[interval] = ohlcv_data

if all_data:
    for interval, data in all_data.items():
        filename = f"{SYMBOL}_{interval}_ohlcv.xlsx"
        save_to_excel(data, filename)
else:
    print("Failed to retrieve any OHLCV data.")
