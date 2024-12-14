
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

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Initialize the sensor
sensor = adafruit_tsl2591.TSL2591(i2c)

async def send(websocket, value, sensorId):
    # Create a JSON payload
    payload = {
        "value": value,
        "sensorId": sensorId
    }
    # Send the JSON payload
    print("Sending payload: ", payload)
    await websocket.send(json.dumps(payload))


async def main():
    print("setting up sensor with ID: ", sensorId)
    uri = "ws://192.168.1.102:8765/ws"  # Ensure this matches your server's route
    try:
        # Open the WebSocket connection once and keep it open
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected")
            while True:
                try:
                    # Read the light level in lux
                    lux = sensor.lux
                    # Read other sensor values if needed
                    infrared = sensor.infrared
                    visible = sensor.visible

                    # Send the lux value via WebSocket
                    await send(websocket, visible, sensorId=sensorId)

                    # Print readings for debugging
                    print(f"Lux: {lux}, Infrared: {infrared}, Visible: {visible}")

                except Exception as e:
                    print(f"Error reading sensor or sending data: {e}")

                # Wait before the next reading
                await asyncio.sleep(1)

    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
