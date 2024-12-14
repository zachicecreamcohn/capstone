
import time
import board
import adafruit_tsl2591
import asyncio
import websockets
import json

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# Initialize the sensor
sensor = adafruit_tsl2591.TSL2591(i2c)


async def send(value, sensorId):
    uri = "ws://192.168.0.100:8765"
    try:
        async with websockets.connect(uri) as websocket:
            # Create a JSON payload
            payload = {
                "value": value,
                "sensorId": sensorId
            }
            # Send the JSON payload
            print("Sending payload: ", payload)
            await websocket.send(json.dumps(payload))
    except Exception as e:
        print(f"WebSocket connection failed: {e}")


async def main():
    while True:
        try:
            # Read the light level in lux
            lux = sensor.lux
            # Read other sensor values if needed
            infrared = sensor.infrared
            visible = sensor.visible

            # Send the lux value via WebSocket
            await send(lux, sensorId=2)

            # Print readings for debugging
            print(f"Lux: {lux}, Infrared: {infrared}, Visible: {visible}")

        except Exception as e:
            print(f"Error reading sensor or sending data: {e}")

        # Wait before the next reading
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
