import asyncio

try:
    loop = asyncio.get_event_loop()
    print("Bucle de eventos actual:", loop)
except RuntimeError as e:
    print("No hay bucle de eventos activo.")
