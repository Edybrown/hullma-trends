import pandas as pd
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

# Cargar los datos desde la base de datos
def load_data(table_name, db_name="crypto_data.db"):
    with sqlite3.connect(db_name) as conn:
        query = f"SELECT * FROM {table_name} ORDER BY timestamp ASC"
        df = pd.read_sql(query, conn)
    df['timestamp'] = pd.to_datetime(df['timestamp'])  # Asegurar formato de fecha
    return df

# Calcular RSI
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Calcular Hull Moving Average
def calculate_hull(df, period=12):
    wma_half = df['close'].rolling(window=period // 2).mean()
    wma_full = df['close'].rolling(window=period).mean()
    hull = (2 * wma_half - wma_full).rolling(window=int(np.sqrt(period))).mean()
    return hull

# Implementar la estrategia: RSI y HullTrend
def strategy(df, rsi_fast_period=8, rsi_slow_period=14, hull_period=12, stop_loss_pct=0.01):
    df['RSI_fast'] = calculate_rsi(df, rsi_fast_period)
    df['RSI_slow'] = calculate_rsi(df, rsi_slow_period)
    df['Hull'] = calculate_hull(df, hull_period)

    df['Signal'] = 0  # 1: Compra, -1: Vende

    # Condiciones para compra
    df.loc[(df['RSI_fast'] < 30) & (df['RSI_slow'] < 30) & (df['Hull'] > df['close']), 'Signal'] = 1
    
    # Condiciones para venta (cuando el precio se mueve en contra un 1% o cuando los indicadores marcan venta)
    df.loc[(df['RSI_fast'] > 70) | (df['RSI_slow'] > 70) | (df['Hull'] < df['close']), 'Signal'] = -1

    df['Stop_loss'] = df['close'] * (1 - stop_loss_pct)  # Precio de stop loss al 1% de la compra

    return df

# Simular las operaciones
def backtest(df, initial_balance=1000, trade_size=1):
    balance = initial_balance
    position = 0  # Estado actual de la posición
    equity_curve = []  # Para guardar el balance en cada paso
    trades = 0
    winning_trades = 0
    losing_trades = 0
    total_profit = 0

    for i in range(1, len(df)):
        price = df['close'].iloc[i]
        signal = df['Signal'].iloc[i]
        stop_loss = df['Stop_loss'].iloc[i]
        
        # Ejecutar compra
        if signal == 1 and position == 0:  # Comprar
            position = trade_size
            buy_price = price
            balance -= position * buy_price
            trades += 1
            print(f"Compra en {price}")

        # Ejecutar venta o stop loss
        elif position > 0:  # Vender
            if price <= stop_loss:  # Si el precio cae un 1%
                balance += position * price
                position = 0
                losing_trades += 1
                print(f"Stop loss: Venta en {price}")
            elif signal == -1:  # Señal de venta
                balance += position * price
                position = 0
                winning_trades += 1
                print(f"Venta en {price}")
        
        # Calcular el equity
        equity = balance + position * price
        equity_curve.append(equity)

    df['Equity'] = equity_curve
    total_profit = df['Equity'].iloc[-1] - initial_balance
    profit_pct = (total_profit / initial_balance) * 100
    win_pct = (winning_trades / trades) * 100 if trades > 0 else 0
    loss_pct = (losing_trades / trades) * 100 if trades > 0 else 0

    # Resultados finales
    print(f"\nBalance final: {df['Equity'].iloc[-1]:.2f} USDT")
    print(f"Operaciones totales: {trades}")
    print(f"Operaciones positivas: {winning_trades}")
    print(f"Operaciones negativas: {losing_trades}")
    print(f"Ganancia total: {total_profit:.2f} USDT")
    print(f"Porcentaje de ganancias: {profit_pct:.2f}%")
    print(f"Porcentaje de operaciones ganadoras: {win_pct:.2f}%")
    print(f"Porcentaje de operaciones perdedoras: {loss_pct:.2f}%")
    
    return df

# Graficar resultados
def plot_results(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['close'], label="Precio", color="blue")
    plt.plot(df['timestamp'], df['Hull'], label="Hull Trend", color="red")
    plt.title("Estrategia: RSI y Hull Trend")
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    plt.plot(df['timestamp'], df['Equity'], label="Curva de Equity", color="purple")
    plt.title("Curva de Equity")
    plt.legend()
    plt.show()

# Script principal
if __name__ == "__main__":
    table_name = "BTC_USDT_5m"  # Tabla con los datos históricos
    df = load_data(table_name)
    df = strategy(df)
    df = backtest(df)
    plot_results(df)
