from pythonosc import udp_client
import logging
import json
import os
from PanTiltPredictor import PanTiltPredictor

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

    def move_to_point(self, x, y, stage_max_y, sensor_coords: dict):
        """
        Expects sensor_coords to be a dictionary with sensor_id as key and a tuple of (x, y) as value.
        """
        # TODO: Make sensor data specific to fixture when storing.
        sensor1_data = self.get_sensor_data(1)
        sensor2_data = self.get_sensor_data(2)
        sensor3_data = self.get_sensor_data(3)
        sensor4_data = self.get_sensor_data(4)

        reference_point1 = (sensor_coords[1][0], sensor_coords[1][1], sensor1_data["pan"], sensor1_data["tilt"])
        reference_point2 = (sensor_coords[2][0], sensor_coords[2][1], sensor2_data["pan"], sensor2_data["tilt"])
        reference_point3 = (sensor_coords[3][0], sensor_coords[3][1], sensor3_data["pan"], sensor3_data["tilt"])
        reference_point4 = (sensor_coords[4][0], sensor_coords[4][1], sensor4_data["pan"], sensor4_data["tilt"])

        pan, tilt = self.predict(x, y, reference_point1, reference_point2, reference_point3, reference_point4, stage_max_y)
        print(f"Pan: {pan}, Tilt: {tilt}")
        self.set_pan(1, 0, pan, "r1", use_degrees=True)
        self.set_tilt(1, 0, tilt, "r1", use_degrees=True)

    @staticmethod
    def invert_y(y, max_y):
        return max_y - y

    def predict(self, target_x, target_y, reference_point1: tuple, reference_point2: tuple, reference_point3: tuple, reference_point4: tuple, stage_max_y):
        predictor = PanTiltPredictor([reference_point1, reference_point2, reference_point3, reference_point4])

        print(f"Target: {target_x}, {target_y}")
        print(f"Reference points: {reference_point1}, {reference_point2}, {reference_point3}, {reference_point4}")
        print(f"Stage max y: {stage_max_y}")
        pan, tilt = predictor.predict_pan_tilt(target_x, self.invert_y(target_y, stage_max_y))
        return pan, tilt
