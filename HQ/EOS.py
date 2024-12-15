from pythonosc import udp_client

# Fixture data with pan and tilt ranges
fixture_data = {
    "r1": {
        "pan": (-270, 270),
        "tilt": (-115, 115),
        "zoom": (12,49)
    }
}

class EOS(object):
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)

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
        else:
            raise ValueError(f"Fixture '{fixture_name}' not found in fixture_data")

    def set_tilt(self, channel: int, current_value: float, move_value: float, fixture_name: str, use_degrees: bool = False) -> None:
        if fixture_name in fixture_data:
            tilt_min, tilt_max = fixture_data[fixture_name]["tilt"]
            actual_tilt_value = self._convert_value(move_value, use_degrees, tilt_min, tilt_max, current_value)
            self.set_parameter(channel, "tilt", actual_tilt_value)
        else:
            raise ValueError(f"Fixture '{fixture_name}' not found in fixture_data")

    def set_zoom(self, channel: int, percent: float, fixture_name: str) -> None:
        """Sets the zoom value for the specified fixture based on a percentage (0-100)."""
        if fixture_name in fixture_data:
            zoom_min, zoom_max = fixture_data[fixture_name]["zoom"]
            actual_zoom_value = self.map_value_to_range(percent, zoom_min, zoom_max)
            self.set_parameter(channel, "zoom", actual_zoom_value)
        else:
            raise ValueError(f"Fixture '{fixture_name}' not found in fixture_data")

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
