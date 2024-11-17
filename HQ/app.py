import json
from flask import Flask, jsonify, request
from flask_sock import Sock

class LightControlApp(Flask):
    def __init__(self, import_name):
        super().__init__(import_name)
        self.sensor_data = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.light_state = {"pan": 50.0, "tilt": 50.0}  # Start at home position
        self._register_routes()

    def _register_routes(self):
        """Define Flask routes."""
        self.add_url_rule('/sensor-data', view_func=self._get_sensor_data, methods=['GET'])
        self.add_url_rule('/control-light', view_func=self._control_light, methods=['POST'])

    def _get_sensor_data(self):
        """Send sensor data as JSON."""
        return jsonify(self.sensor_data)

    def _control_light(self):
        """Accept and apply pan/tilt commands."""
        data = request.get_json()
        self.light_state.update({key: data[key] for key in ["pan", "tilt"] if key in data})
        print(f"Light moved to pan: {self.light_state['pan']}, tilt: {self.light_state['tilt']}")
        return jsonify({"status": "success"})

    def update_sensor_data(self, sensor_ID, intensity):
        """Update the app's sensor data."""
        if sensor_ID in self.sensor_data:
            self.sensor_data[sensor_ID] = intensity
            print(f"Sensor {sensor_ID} updated with intensity: {intensity}")
        else:
            print(f"Sensor {sensor_ID} not found in sensor data.")


# Create the Flask app and integrate Flask-Sock
app = LightControlApp(__name__)
sock = Sock(app)


@sock.route('/ws')
def websocket_handler(ws):
    """Handle WebSocket connections."""
    while True:
        message = ws.receive()
        # make sure data is in the format:
        ## {"sesnorID": 1, "intensity": 0.5}
        json_data = json.loads(message)
        if json_data.get("sensorID") and json_data.get("intensity"):
            app.update_sensor_data(json_data["sensorID"], json_data["intensity"])
        else:
            # send error message
            ws.send("Invalid data format. Please send data in the format: {'sensorID': 1, 'intensity': 0.5}")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3456)
