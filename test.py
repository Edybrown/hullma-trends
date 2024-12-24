import websocket
import json
import time

websocket.enableTrace(True)  # Habilita la depuración de WebSocket

def on_message(ws, message):
    print("Mensaje recibido:", message)

def on_error(ws, error):
    print(f"Error en la conexión: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Conexión cerrada. Código: {close_status_code}, Mensaje: {close_msg}")

def on_open(ws):
    print("Conexión establecida.")
    subscription_message = {
        "method": "state.subscribe",
        "params": ["BTCUSDT"],  # Cambiar al mercado deseado
        "id": 1
    }
    ws.send(json.dumps(subscription_message))

def test_websocket():
    websocket_url = "wss://socket.coinex.com/v2/spot"
    ws = websocket.WebSocketApp(
        websocket_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    try:
        while True:
            try:
                print("Intentando conectar...")
                ws.run_forever(ping_interval=30)
            except Exception as e:
                print(f"Error: {e}. Reintentando en 5 segundos...")
                time.sleep(5)
    except KeyboardInterrupt:
        print("Conexión finalizada por el usuario.")

if __name__ == "__main__":
    test_websocket()
