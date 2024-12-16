from enum import Enum
from EOS import EOS
from gevent import sleep
import logging

class Phase(Enum):
    SETUP = "setup"
    OPTIMIZE = "optimize"
    COMPLETE = "complete"
    FAILED = "failed"

class Navigator:
    def __init__(self, eos_ip="192.168.1.105", eos_port=8000, sensor_data=None, lock=None):
        self.eos = EOS(eos_ip, eos_port)
        self.current_phase = Phase.SETUP
        self.pan = 0.0
        self.tilt = 0.0
        self.best_intensity = -1
        self.target_sensor = 1
        self.sensor_data = sensor_data
        self.lock = lock

    def send_light_command(self, pan_move, tilt_move, use_degrees=True):
        # Send pan/tilt updates to EOS
        self.eos.set_pan(1, self.pan, pan_move, "r1", use_degrees)
        self.eos.set_tilt(1, self.tilt, tilt_move, "r1", use_degrees)
        self.pan += pan_move
        self.tilt += tilt_move
        logging.debug(f"Sent pan_move: {pan_move}, tilt_move: {tilt_move}. New pan: {self.pan}, New tilt: {self.tilt}")

    def setup_phase(self):
        logging.info("Entering SETUP phase.")
        self.eos.set_intensity(1, 100)
        sleep(0.5)  # Reduced sleep for quicker updates

        with self.lock:
            self.best_intensity = self.sensor_data.get(self.target_sensor, 0)
            logging.debug(f"Setup complete. Baseline intensity: {self.best_intensity}")

        return Phase.OPTIMIZE

    def optimize_phase(self):
        logging.info("Entering OPTIMIZE phase.")

        with self.lock:
            initial_intensity = self.sensor_data.get(self.target_sensor, 0)
            logging.debug(f"Initial intensity before adjustment: {initial_intensity}")

        self.send_light_command(pan_move=5, tilt_move=5)  # Example move
        self.eos.set_intensity(1, 0)
        logging.debug("Light intensity set to 0.")
        sleep(0.5)  # Adjust based on sensor response time

        with self.lock:
            updated_intensity = self.sensor_data.get(self.target_sensor, 0)
            logging.debug(f"Intensity after adjustment: {updated_intensity}")

        if initial_intensity != updated_intensity:
            logging.info("They are not equal")
            return Phase.COMPLETE
        else:
            logging.info("They are equal")
            return Phase.COMPLETE  # Or return Phase.OPTIMIZE to continue optimizing

    def execute(self):
        logging.debug(f"Executing phase: {self.current_phase}")
        if self.current_phase == Phase.SETUP:
            self.current_phase = self.setup_phase()
        elif self.current_phase == Phase.OPTIMIZE:
            self.current_phase = self.optimize_phase()

        return {
            "current_phase": self.current_phase.name,
            "pan": self.pan,
            "tilt": self.tilt,
            "target_sensor": self.target_sensor,
        }
