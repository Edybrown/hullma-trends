import websocket

def on_error(ws, error):
    logging.error(f"Error en la conexión WebSocket: {error}")
    # Intenta reconectar con un retraso
    time.sleep(5)
    connect_websocket()

def connect_websocket():
    global ws
    websocket_url = "wss://socket.coinex.com/v2/spot"
    while True:
        try:
            ws = websocket.WebSocketApp(websocket_url,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
            ws.run_forever(ping_interval=30)
        except Exception as e:
            logging.error(f"Error en la conexión WebSocket: {e}")
            logging.info("Intentando reconectar en 5 segundos...")
            time.sleep(5)
