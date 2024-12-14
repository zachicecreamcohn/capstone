import asyncio
import websockets

async def test_connection():
    uri = "ws://192.168.1.102:8765/ws"  # Replace with your computer's IP address
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            message = "Hello, Server!"
            print(f"Sending message: {message}")
            await websocket.send(message)
            response = await websocket.recv()
            print(f"Received response: {response}")
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_connection())
