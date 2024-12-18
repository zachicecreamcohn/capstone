from pythonosc import udp_client
import logging
import json
import os
from PanTiltPredictor import PanTiltPredictor



logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class EOS(object):
    def __init__(self, ip: str, port: int, recalibrate_state: dict = {"recalibrate": False}, fixtures_file: str = ".fixtures.json"):
        self.ip = ip
        self.port = port
        self.recalibrate_state = recalibrate_state
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.sensor_data= {1:{1:{"pan":0.0,"tilt":0.0, "direction": 1}, 2:{"pan":0.0,"tilt":0.0, "direction": 1}, 3:{"pan":0.0,"tilt":0.0, "direction": 1}, 4:{"pan":0.0,"tilt":0.0, "direction": 1}}}
        self.fixtures_file = fixtures_file
        self.fixture_data = self.load_fixtures()
        self.fixture_positions = {}
        self.current_data = {}

    def load_fixtures(self):
        """
        Load fixture data from .fixtures.json. Create the file if it doesn't exist.
        """
        if not os.path.exists(self.fixtures_file):
            with open(self.fixtures_file, "w") as f:
                json.dump({}, f)  # Initialize with an empty dictionary
            logging.info(f"{self.fixtures_file} created.")

        try:
            with open(self.fixtures_file, "r") as f:
                fixture_data = json.load(f)
                logging.info(f"Fixture data loaded: {fixture_data}")
                return fixture_data
        except json.JSONDecodeError:
            logging.error(f"Failed to decode {self.fixtures_file}. Resetting file.")
            with open(self.fixtures_file, "w") as f:
                json.dump({}, f)
            return {}

    def save_fixtures(self):
        """
        Save the current fixture data to the .fixtures.json file.
        """
        with open(self.fixtures_file, "w") as f:
            json.dump(self.fixture_data, f, indent=4)
        logging.info("Fixture data saved successfully.")

    def get_list_of_fixtures(self):
        # reread fixtures file
        self.fixture_data = self.load_fixtures()
        return list(self.fixture_data.keys())

    def get_pan_range(self, channel: str):
        """
        Retrieve the pan range for a specific fixture.
        """
        if channel in self.fixture_data:
            return tuple(self.fixture_data[channel].get("pan", (-270, 270)))
        raise ValueError(f"Fixture '{channel}' not found in fixture_data.")

    def get_tilt_range(self, channel: str):
        """
        Retrieve the tilt range for a specific fixture.
        """
        if channel in self.fixture_data:
            return tuple(self.fixture_data[channel].get("tilt", (-115, 115)))
        raise ValueError(f"Fixture '{channel}' not found in fixture_data.")

    def send(self, message: str, value: str or int or float):
        self.client.send_message(message, value)

    def set_intensity(self, channel: int, value: float) -> None:
        self.send(f"/eos/chan/{channel}/intensity", value)

    def set_parameter(self, channel: int, parameter: str, value: float) -> None:
        self.send(f"/eos/chan/{channel}/param/{parameter}", value)

    def map_value_to_range(self, percent: float, min_value: float, max_value: float) -> float:
        """Maps a percentage (0-100) to a value within the specified range."""
        return (percent / 100) * (max_value - min_value) + min_value

    def set_pan(self, channel: int, current_value: float, move_value: float, use_degrees: bool = False):
            channel_str = str(channel)
            if channel_str in self.fixture_data:
                pan_min, pan_max = self.get_pan_range(channel_str)
                actual_pan_value = self._convert_value(move_value, use_degrees, pan_min, pan_max, current_value)
                self.set_parameter(channel, "pan", actual_pan_value)
                if channel not in self.current_data:
                    self.current_data[channel] = {}

                self.current_data[channel]["pan"] = actual_pan_value
            else:
                raise ValueError(f"Channel '{channel}' not found in fixture_data.")

    def set_tilt(self, channel: int, current_value: float, move_value: float, use_degrees: bool = False):
        channel_str = str(channel)
        if channel_str in self.fixture_data:
            tilt_min, tilt_max = self.get_tilt_range(channel_str)
            actual_tilt_value = self._convert_value(move_value, use_degrees, tilt_min, tilt_max, current_value)
            self.set_parameter(channel, "tilt", actual_tilt_value)
            if channel not in self.current_data:
                self.current_data[channel] = {}

            self.current_data[channel]["tilt"] = actual_tilt_value
        else:
            raise ValueError(f"Channel '{channel}' not found in fixture_data.")

    def get_pan(self, channel: int) -> float:
        return self.current_data[channel]["pan"]

    def get_tilt(self, channel: int) -> float:
        return self.current_data[channel]["tilt"]

    def set_sensor_data(self, sensor_id: int, pan: float, tilt: float, direction: int, channel) -> None:

        if channel not in self.sensor_data:
            self.sensor_data[channel] = {}

        if sensor_id not in self.sensor_data[channel]:
            self.sensor_data[channel][sensor_id] = {}

        self.sensor_data[channel][sensor_id] = {"pan": pan, "tilt": tilt, "direction": direction}

        # write to local .sensors file
        with open(".sensors.json", "w") as f:
            json.dump(self.sensor_data, f)

    def get_sensor_data(self, sensor_id: int, channel) -> dict:
        if not self.sensors_data_file_is_valid():
            raise ValueError("Invalid sensor data file or sensor data not found.")
        with open(".sensors.json", "r") as f:
            self.sensor_data = json.load(f)


        return self.sensor_data[channel][str(sensor_id)]

    def sensors_data_file_is_valid(self) -> bool:
        if os.path.exists(".sensors.json"):
            with open(".sensors.json", "r") as f:
                self.sensor_data = json.load(f)
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

    def move_to_point(self, x, y, stage_max_y, sensor_coords: dict, channel: int):
        """
        Expects sensor_coords to be a dictionary with sensor_id as key and a tuple of (x, y) as value.
        """
        sensor1_data = self.get_sensor_data(1, channel)
        sensor2_data = self.get_sensor_data(2, channel)
        sensor3_data = self.get_sensor_data(3, channel)
        sensor4_data = self.get_sensor_data(4, channel)

        reference_point1 = (sensor_coords[1][0], sensor_coords[1][1], sensor1_data["pan"], sensor1_data["tilt"])
        reference_point2 = (sensor_coords[2][0], sensor_coords[2][1], sensor2_data["pan"], sensor2_data["tilt"])
        reference_point3 = (sensor_coords[3][0], sensor_coords[3][1], sensor3_data["pan"], sensor3_data["tilt"])
        reference_point4 = (sensor_coords[4][0], sensor_coords[4][1], sensor4_data["pan"], sensor4_data["tilt"])

        pan, tilt = self.predict(x, y, reference_point1, reference_point2, reference_point3, reference_point4, stage_max_y)
        print(f"Pan: {pan}, Tilt: {tilt}")
        self.set_pan(channel, 0, self._get_nearest_pan(channel,pan), use_degrees=True)
        self.set_tilt(channel, 0, tilt, use_degrees=True)

    def _get_nearest_pan(self, channel: int, target_pan: float) -> float:
        pan_min, pan_max = self.get_pan_range(str(channel))
        current_pan = self.current_data.get(channel, {}).get("pan", 0.0)

        # Normalize target_pan to be within -180° to +180°
        target_pan_normalized = ((target_pan + 180) % 360) - 180

        # Generate equivalent pans within the allowed range
        equivalent_pans = [target_pan_normalized + k * 360 for k in range(-1, 2)]
        valid_pans = [pan for pan in equivalent_pans if pan_min <= pan <= pan_max]

        if not valid_pans:
            raise ValueError(f"No valid pan found for target_pan {target_pan}° within range ({pan_min}°, {pan_max}°)")

        # Select the pan closest to the current pan
        nearest_pan = min(valid_pans, key=lambda pan: abs(pan - current_pan))

        logging.info(f"Current Pan: {current_pan}°, Target Pan: {target_pan}°, Nearest Pan: {nearest_pan}°")
        return nearest_pan



    @staticmethod
    def invert_y(y, max_y):
        return max_y - y

    def predict(self, target_x, target_y, reference_point1: tuple, reference_point2: tuple, reference_point3: tuple, reference_point4: tuple, stage_max_y):
        predictor = PanTiltPredictor([reference_point1, reference_point2, reference_point3, reference_point4])

        pan, tilt = predictor.predict_pan_tilt(target_x, self.invert_y(target_y, stage_max_y))
        return pan, tilt
