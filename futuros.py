import requests
import time
import csv


# Base URL for accessing Coinanalyze data (ensure it includes the version)
base_url = "https://api.coinalyze.net/v1"

# Function to construct the URL with API key
def construct_url(endpoint, params):
    """
    Constructs a URL for the Coinanalyze API, including the API key as a parameter.

    Args:
        endpoint (str): The API endpoint (e.g., "/ohlcv-history").
        params (dict): A dictionary of parameters for the request.

    Returns:
        str: The complete URL with API key included.
    """

    params["api_key"] = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"  # Replace with your actual API key
    url = f"{base_url}{endpoint}"
    return url


# Function to make the API request
def get_data(url):
    """
    Makes a GET request to the Coinanalyze API and returns the response data.

    Args:
        url (str): The complete URL for the API request.

    Returns:
        dict or None: The JSON data from the response if successful, otherwise None.
    """

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error in request to {url}: {response.status_code} {response.reason}")
        print("Error details (JSON):", response.json())
        return None


# Function to save data to a CSV file
def save_to_csv(filename, data, header):
    """
    Saves data to a CSV file.

    Args:
        filename (str): The name of the CSV file.
        data (list): A list of dictionaries containing the data to save.
        header (list): A list of column names for the CSV file.
    """

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)


# Example usage
if __name__ == "__main__":
    # Replace with symbols you want to check, including "BINANCE:BTCUSDT_SPOT" for BTC spot
    symbols = ["BINANCE:BTCUSDT_SPOT", "OTHER_SYMBOL1", "OTHER_SYMBOL2"]

    # Construct the URL for the list-exchanges endpoint
    url = construct_url("/list-exchanges", {})

    # Get exchange information
    exchange_data = get_data(url)

    if exchange_data:
        # Extract spot markets for the exchange where BTC is traded
        spot_markets = []
        for exchange in exchange_data["data"]:
            for market in exchange["markets"]:
                if market["baseAsset"] == "BTC" and market["quoteAsset"] == "USDT" and market["type"] == "SPOT":
                    spot_markets.append(market["symbol"])

        # Print or use the spot_markets list for further processing
        if spot_markets:
            print("BTC Spot symbols:")
            for symbol in spot_markets:
                print(symbol)
        else:
            print("No BTC Spot symbols found for the listed exchanges.")
    else:
        print("Error retrieving exchange data.")
