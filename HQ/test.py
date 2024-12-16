import asyncio
from websockets.asyncio.server import serve


async def echo(websocket):
    async for message in websocket:
        print(f"Received message: {message}")
        await websocket.send(message)


async def main():
    # Bind to 0.0.0.0 to allow external connections
    async with serve(echo, "0.0.0.0", 8765) as server:
        await server.serve_forever()


if __name__ == "__main__":
    print("Starting server")


    asyncio.run(main())
