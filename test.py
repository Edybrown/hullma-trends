import websocket
import json

def test_connection():
    try:
        ws = websocket.create_connection("wss://socket.coinex.com/v2/spot")
        MARKET = "BTCUSDT"  # Asegúrate de definir el mercado
        ws.send(json.dumps({"method": "state.subscribe", "params": [MARKET], "id": 1}))
        response = ws.recv()
        print(response)
        ws.close()
    except Exception as e:
        print(f"Error de conexión: {e}")

test_connection()
