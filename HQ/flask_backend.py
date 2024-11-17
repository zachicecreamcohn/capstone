class FlaskBackend:
    def __init__(self, app):
        """
        Initialize the FlaskBackend with a reference to the Flask app.

        :param app: An instance of the Flask app (e.g., LightControlApp).
        """
        self.app = app

    def get_sensor_data(self):
        """
        Retrieve the current sensor data from the app.
        :return: Dictionary of sensor intensities.
        """
        return self.app.sensor_data

    def send_light_command(self, pan, tilt):
        """
        Update the light state in the app with new pan and tilt values.

        :param pan: Pan percentage (0-100).
        :param tilt: Tilt percentage (0-100).
        """
        self.app.light_state["pan"] = pan
        self.app.light_state["tilt"] = tilt
