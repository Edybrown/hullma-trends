import requests
import json
import time
import datetime
import csv

# ***¡REEMPLAZA ESTO CON TU CLAVE API REAL!***
api_key = "6ecb2327-4d0c-49c8-9e96-2f5028891e1d"

base_url = "https://api.coinalyze.net/v1"

def get_data(endpoint, params, use_header=True):
    """Realiza una solicitud a la API de Coinanalyze con autenticación."""
    headers = {}
    if use_header:
        headers = {"Authorization": f"Bearer {api_key}"}
    elif params:
        params['api_key'] = api_key
    url = f"{base_url}{endpoint}"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP en {url}: {http_err}")
        if http_err.response is not None:
            try:
                error_json = http_err.response.json()
                print(f"Detalles del error (JSON): {json.dumps(error_json, indent=4)}")
            except json.JSONDecodeError:
                print(f"Detalles del error (Texto): {http_err.response.text}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud a {url}: {err}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}")
        return None


def get_future_markets():
    """Obtiene la lista de mercados de futuros."""
    endpoint = "/future-markets"
    return get_data(endpoint, None, use_header=False) #Este endpoint no requiere autenticacion con header

def save_to_csv(filename, data, header):
    """Guarda los datos en un archivo CSV."""
    if data is None or not data: #Comprobacion de que data no este vacio o sea None
        print(f"No hay datos para guardar en {filename}")
        return
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        writer.writerows(data)
    print(f"Datos guardados en {filename}")

def get_data_with_symbol(endpoint, symbol, interval, from_timestamp, to_timestamp, use_header = True):
    """Obtiene datos con símbolo, intervalo y rango de tiempo."""
    params = {
        'symbols': symbol,
        'interval': interval,
        'from': from_timestamp,
        'to': to_timestamp
    }
    data = get_data(endpoint, params, use_header)
    return data.get('data') if data else None

if __name__ == "__main__":
    future_markets = get_future_markets()

    if future_markets:
        # Encuentra un símbolo de BTCUSDT_PERP en Binance
        btc_symbol = next((m['symbol'] for m in future_markets if m['exchange'] == 'BINANCE' and m['baseAsset'] == 'BTC' and m['quoteAsset'] == 'USDT' and m['is_perpetual'] == True), None)

        if btc_symbol:
            print(f"Usando el símbolo: {btc_symbol}")
            interval = "1hour"
            dias_atras = 7
            to_timestamp = int(time.time())
            from_timestamp = to_timestamp - (dias_atras * 24 * 60 * 60)

            #Prueba con header y con params
            for use_header in [True, False]:
                print(f"\n--- Probando con {'Header' if use_header else 'Params'} ---")
                # Obtener y guardar datos
                ohlcv_data = get_data_with_symbol("/ohlcv-history", btc_symbol, interval, from_timestamp, to_timestamp, use_header)
                save_to_csv("ohlcv_data.csv", ohlcv_data, ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])

                funding_rate_data = get_data_with_symbol("/funding-rate-history", btc_symbol, interval, from_timestamp, to_timestamp, use_header)
                save_to_csv("funding_rate_data.csv", funding_rate_data, ['timestamp', 'symbol', 'fundingRate'])

                liquidation_data = get_data_with_symbol("/liquidation-history", btc_symbol, None, from_timestamp, to_timestamp, use_header) #intervalo no necesario
                save_to_csv("liquidation_history.csv", liquidation_data, ['timestamp', 'symbol', 'liquidationPrice'])

                open_interest_data = get_data_with_symbol("/open-interest-history", btc_symbol, interval, from_timestamp, to_timestamp, use_header)
                save_to_csv("open_interest_data.csv", open_interest_data, ['timestamp', 'symbol', 'openInterest'])

                long_short_ratio_data = get_data_with_symbol("/long-short-ratio-history", btc_symbol, interval, from_timestamp, to_timestamp, use_header)
                save_to_csv("long_short_ratio_data.csv", long_short_ratio_data, ['timestamp', 'symbol', 'longShortRatio'])

        else:
            print("No se encontró un símbolo BTCUSDT_PERP en Binance.")
    else:
        print("Error al obtener la lista de mercados de futuros.")
