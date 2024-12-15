from enum import Enum
import numpy as np
from EOS import EOS
from gevent import sleep

class Phase(Enum):
    EXPLORATORY = "exploratory"
    DIRECTED = "directed"
    VERIFICATION = "verification"
    COMPLETE = "complete"
    VERIFICATION_FAILED = "verification_failed"


class Navigator:
    def __init__(self, sensors_data, persisted_state=None):
        self.step_size = 2
        self.tolerance = 0.1
        self.pan = 50
        self.tilt = 60.0
        self.sensors_data = sensors_data
        self.target_sensor = None
        self.eos= EOS("192.168.1.105", 8000)

        # Restore persisted state
        self.current_phase = (
            Phase[persisted_state.get("current_phase")] if persisted_state else Phase.EXPLORATORY
        )
        self.pan = persisted_state.get("pan", 50.0) if persisted_state else 50.0
        self.tilt = persisted_state.get("tilt", 50.0) if persisted_state else 50.0
        self.target_sensor = persisted_state.get("target_sensor", None) if persisted_state else None
        self.previous_intensity = persisted_state.get("previous_intensity", -1) if persisted_state else -1

    def send_light_command(self, pan, tilt):
        # TODO here is where i need to call/import a class that handles light movements
        self.pan = pan
        self.tilt = tilt
        self.eos.set_pan(1, pan, "r2x") # TODO find another way to pass fixture type
        self.eos.set_tilt(1, tilt, "r2x") # TODO find another way to pass fixture type


    def exploratory_phase(self):
        radius = self.tilt
        direction = 1

        # Incrementally perform the exploratory sweep
        radius += self.step_size
        if radius > 100 or radius < 0:
            return Phase.DIRECTED

        for pan in np.arange(00, 100 + direction, direction * self.step_size):
            self.send_light_command(pan, radius)
            # sleep 1 second
            sleep(0.05)
            if self.detect_significant_change():
                return Phase.DIRECTED

        return Phase.EXPLORATORY

    def detect_significant_change(self):
        for sensor, intensity in self.sensors_data.items():
            if intensity > self.tolerance:
                self.target_sensor = sensor
                return True
        return False

    def directed_phase(self):
        target_intensity = self.sensors_data.get(self.target_sensor, 0)

        if target_intensity <= self.previous_intensity:
            return Phase.VERIFICATION

        self.pan += self.step_size * (1 if target_intensity > self.previous_intensity else -1)
        self.tilt += self.step_size * (1 if target_intensity > self.previous_intensity else -1)

        self.send_light_command(self.pan, self.tilt)
        self.previous_intensity = target_intensity

        return Phase.DIRECTED

    def verification_phase(self):
        directions = [(self.step_size, 0), (-self.step_size, 0), (0, self.step_size), (0, -self.step_size)]
        initial_intensity = self.sensors_data.get(self.target_sensor, 0)

        for d_pan, d_tilt in directions:
            self.send_light_command(self.pan + d_pan, self.tilt + d_tilt)
            if self.sensors_data.get(self.target_sensor, 0) >= initial_intensity:
                return Phase.VERIFICATION_FAILED

        return Phase.COMPLETE

    def execute(self):
        # print the current phase
        print(f"Phase : {self.current_phase.name}")

        if self.current_phase == Phase.EXPLORATORY:
            self.current_phase = self.exploratory_phase()

        if self.current_phase == Phase.DIRECTED:
            self.current_phase = self.directed_phase()

        if self.current_phase == Phase.VERIFICATION:
            self.current_phase = self.verification_phase()

        return {
            "current_phase": self.current_phase.name,
            "pan": self.pan,
            "tilt": self.tilt,
            "target_sensor": self.target_sensor,
            "previous_intensity": self.previous_intensity,
        }
