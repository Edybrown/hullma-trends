import sqlite3
import pandas as pd

# Conectar a la base de datos
def read_from_database(table_name, db_name="crypto_data.db", limit=100):
    with sqlite3.connect(db_name) as conn:
        query = f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql(query, conn)
    return df

# Consultar los datos
def main():
    table_name = "BTC_USDT_5m"  # Nombre de la tabla que quieres consultar
    db_name = "crypto_data.db"
    
    print(f"Consultando datos de la tabla {table_name}...")
    df = read_from_database(table_name, db_name)
    
    print("Primeros datos:")
    print(df.head())  # Muestra las primeras filas del DataFrame
    
    # Opcional: Visualiza los datos
    print("\nDescripción de los datos:")
    print(df.describe())
    
if __name__ == "__main__":
    main()
