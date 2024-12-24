import websocket

def test_connection():
    try:
        ws = websocket.create_connection("wss://socket.coinex.com/v2/spot")
        ws.send(json.dumps({"method": "state.subscribe", "params": [MARKET], "id": 1}))
        response = ws.recv()
        print(response)
        ws.close()
    except Exception as e:
        print(f"Error de conexión: {e}")

test_connection()
