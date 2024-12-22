import ccxt
import pandas as pd
import sqlite3
from datetime import datetime
import os

# Configura el exchange
def fetch_data(symbol, timeframe, since=None, limit=1000):
    exchange = ccxt.binance({
        'rateLimit': 1200,
        'enableRateLimit': True,
    })
    
    data = []
    while True:
        # Obtén datos OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if len(ohlcv) == 0:
            break
        data.extend(ohlcv)
        since = ohlcv[-1][0] + 1  # Evitar duplicados
    
    return data

# Convierte datos en DataFrame
def ohlcv_to_dataframe(data):
    columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    df = pd.DataFrame(data, columns=columns)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # Convierte el timestamp
    return df

# Guarda datos en SQLite
def save_to_database(df, table_name, db_name="crypto_data.db"):
    with sqlite3.connect(db_name) as conn:
        df.to_sql(table_name, conn, if_exists='append', index=False)
    print(f"Datos guardados en {table_name} de {db_name}")

# Descargar y almacenar datos
def main():
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Activos a descargar
    timeframes = ['5m', '15m', '1h']  # Temporalidades
    db_name = "crypto_data.db"
    
    for symbol in symbols:
        for timeframe in timeframes:
            print(f"Descargando {symbol} en {timeframe}...")
            data = fetch_data(symbol, timeframe)
            df = ohlcv_to_dataframe(data)
            table_name = f"{symbol.replace('/', '_')}_{timeframe}"
            save_to_database(df, table_name, db_name)

    print("Directorio actual:", os.getcwd())

if __name__ == "__main__":
    main()
