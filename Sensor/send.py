import time
import board
import adafruit_tsl2591
import asyncio
import websockets
import json
from dotenv import load_dotenv
import os

load_dotenv('.env')

sensorId = os.getenv("SENSOR_ID")

i2c = board.I2C()
sensor = adafruit_tsl2591.TSL2591(i2c)

async def send(websocket, value, sensorId):
    payload = {
        "value": value,
        "sensorId": sensorId
    }
    print("Sending payload:", payload)
    await websocket.send(json.dumps(payload))

async def main():
    print("Setting up sensor with ID:", sensorId)
    uri = "ws://192.168.1.102:8765/ws"

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("WebSocket connected")
                while True:
                    try:
                        lux = sensor.lux
                        infrared = sensor.infrared
                        visible = sensor.visible
                        await send(websocket, visible, sensorId=sensorId)
                    except Exception as e:
                        print(f"Error reading sensor or sending data: {e}")
                        # attempt to reconnect
                        break
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            print("Retrying connection in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
