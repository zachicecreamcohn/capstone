from pythonosc import udp_client
import logging
import json
import os

# Fixture data with pan and tilt ranges
fixture_data = {
    "r1": {
        "pan": (-270, 270),
        "tilt": (-115, 115),
        "zoom": (12,49),
    }
}

current_data = {}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class EOS(object):
    def __init__(self, ip: str, port: int, recalibrate_state: dict = {"recalibrate": False}):
        self.ip = ip
        self.port = port
        self.recalibrate_state = recalibrate_state
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.sensor_data= {1:{"pan":0.0,"tilt":0.0, "direction": 1}, 2:{"pan":0.0,"tilt":0.0, "direction": 1}, 3:{"pan":0.0,"tilt":0.0, "direction": 1}, 4:{"pan":0.0,"tilt":0.0, "direction": 1}}

    def send(self, message: str, value: str or int or float):
        self.client.send_message(message, value)

    def set_intensity(self, channel: int, value: float) -> None:
        self.send(f"/eos/chan/{channel}/intensity", value)

    def set_parameter(self, channel: int, parameter: str, value: float) -> None:
        self.send(f"/eos/chan/{channel}/param/{parameter}", value)

    def map_value_to_range(self, percent: float, min_value: float, max_value: float) -> float:
        """Maps a percentage (0-100) to a value within the specified range."""
        return (percent / 100) * (max_value - min_value) + min_value

    def get_pan_range(self, fixture_name: str):
        return fixture_data[fixture_name]["pan"]

    def get_tilt_range(self, fixture_name: str):
        return fixture_data[fixture_name]["tilt"]

    def set_pan(self, channel: int, current_value: float, move_value: float, fixture_name: str, use_degrees: bool = False) -> None:
        if fixture_name in fixture_data:
            pan_min, pan_max = fixture_data[fixture_name]["pan"]
            actual_pan_value = self._convert_value(move_value, use_degrees, pan_min, pan_max, current_value)
            self.set_parameter(channel, "pan", actual_pan_value)
            if channel not in current_data:
                current_data[channel] = {}

            current_data[channel]["pan"] = actual_pan_value
        else:
            raise ValueError(f"Fixture '{fixture_name}' not found in fixture_data")

    def set_tilt(self, channel: int, current_value: float, move_value: float, fixture_name: str, use_degrees: bool = False) -> None:
        if fixture_name in fixture_data:
            tilt_min, tilt_max = fixture_data[fixture_name]["tilt"]
            actual_tilt_value = self._convert_value(move_value, use_degrees, tilt_min, tilt_max, current_value)
            self.set_parameter(channel, "tilt", actual_tilt_value)
            if channel not in current_data:
                current_data[channel] = {}

            current_data[channel]["tilt"] = actual_tilt_value
        else:
            raise ValueError(f"Fixture '{fixture_name}' not found in fixture_data")

    def get_pan(self, channel: int) -> float:
        return current_data[channel]["pan"]

    def get_tilt(self, channel: int) -> float:
        return current_data[channel]["tilt"]

    def set_sensor_data(self, sensor_id: int, pan: float, tilt: float, direction: int) -> None:
        self.sensor_data[sensor_id] = {"pan": pan, "tilt": tilt, "direction": direction}
        # write to local .sensors file
        with open(".sensors.json", "w") as f:
            json.dump(self.sensor_data, f)

    def get_sensor_data(self, sensor_id: int) -> dict:
        if not self.sensors_data_file_is_valid():
            raise ValueError("Invalid sensor data file or sensor data not found.")
        with open(".sensors.json", "r") as f:
            self.sensor_data = json.load(f)

        return self.sensor_data[str(sensor_id)]

    def sensors_data_file_is_valid(self) -> bool:
        if os.path.exists(".sensors.json"):
            with open(".sensors.json", "r") as f:
                self.sensor_data = json.load(f)
            for sensor_id in self.sensor_data:
                if "pan" not in self.sensor_data[sensor_id] or "tilt" not in self.sensor_data[sensor_id]:
                    logging.error(f"Sensor data for sensor {sensor_id} is invalid.")
                    return False
            logging.debug("Sensor data file found and loaded.")
            return True
        logging.error("Sensor data file not found.")
        return False

    def _convert_value(self, move_value: float, use_degrees: bool, min_value: float, max_value: float, current_value: float) -> float:
        if use_degrees:
            new_value = current_value + move_value
            if not min_value <= new_value <= max_value:
                raise ValueError(f"Requested move {move_value}° results in {new_value}°, which is out of range ({min_value}° to {max_value}°)")
            return float(new_value)
        else:
            mapped_value = (move_value / 100) * (max_value - min_value) + min_value
            new_value = current_value + mapped_value
            if not min_value <= new_value <= max_value:
                raise ValueError(f"Requested move {move_value}% results in {new_value}°, which is out of range ({min_value}° to {max_value}°)")
            return float(new_value)

    def move_to_point(self, x: float, y: float, sensor_1_coords: tuple, sensor_2_coords: tuple, sensor_3_coords: tuple, sensor_4_coords: tuple, fixture_name: str) -> None:
        points = [
            {"x": sensor_1_coords[0], "y": sensor_1_coords[1], "pan": self.sensor_data[1]["pan"], "tilt": self.sensor_data[1]["tilt"]},
            {"x": sensor_2_coords[0], "y": sensor_2_coords[1], "pan": self.sensor_data[2]["pan"], "tilt": self.sensor_data[2]["tilt"]},
            {"x": sensor_3_coords[0], "y": sensor_3_coords[1], "pan": self.sensor_data[3]["pan"], "tilt": self.sensor_data[3]["tilt"]},
            {"x": sensor_4_coords[0], "y": sensor_4_coords[1], "pan": self.sensor_data[4]["pan"], "tilt": self.sensor_data[4]["tilt"]}
        ]

        # get the pan and tilt values for the target point
        pan, tilt = self.barycentric_interpolation(x, y, points)

        # set the pan and tilt values for the target point
        self.set_pan(1, self.sensor_data[1]["pan"], pan, fixture_name)
        self.set_tilt(1, self.sensor_data[1]["tilt"], tilt, fixture_name)


    def barycentric_interpolation(self, x, y, points):
        """
        Parameters:
        - x, y: Coordinates of the target point.
        - points: A list of dictionaries with structure:
            [{"x": x1, "y": y1, "pan": pan1, "tilt": tilt1}, ...]

        Returns:
        - (pan, tilt): Predicted pan and tilt for the target point.
        """
        def barycentric_coords(px, py, p1, p2, p3):
            # Compute barycentric coordinates for point (px, py) in triangle p1, p2, p3
            denom = (p2['y'] - p3['y'])*(p1['x'] - p3['x']) + (p3['x'] - p2['x'])*(p1['y'] - p3['y'])
            l1 = ((p2['y'] - p3['y'])*(px - p3['x']) + (p3['x'] - p2['x'])*(py - p3['y'])) / denom
            l2 = ((p3['y'] - p1['y'])*(px - p3['x']) + (p1['x'] - p3['x'])*(py - p3['y'])) / denom
            l3 = 1 - l1 - l2
            return l1, l2, l3

        # Split the quadrilateral into two triangles
        P1, P2, P3, P4 = points

        # Check which triangle the point (x, y) falls in
        l1, l2, l3 = barycentric_coords(x, y, P1, P2, P3)
        if all(0 <= l <= 1 for l in [l1, l2, l3]):
            pan = l1 * P1['pan'] + l2 * P2['pan'] + l3 * P3['pan']
            tilt = l1 * P1['tilt'] + l2 * P2['tilt'] + l3 * P3['tilt']
            return pan, tilt

        l1, l2, l3 = barycentric_coords(x, y, P3, P4, P1)
        pan = l1 * P3['pan'] + l2 * P4['pan'] + l3 * P1['pan']
        tilt = l1 * P3['tilt'] + l2 * P4['tilt'] + l3 * P1['tilt']
        return pan, tilt
