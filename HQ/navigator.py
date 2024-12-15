from enum import Enum
import numpy as np
from EOS import EOS
from gevent import sleep

class Phase(Enum):
    EXPLORATORY = "exploratory"
    EXPLORATORY_FAILED = "exploratory_failed"
    DIRECTED = "directed"
    VERIFICATION = "verification"
    COMPLETE = "complete"
    VERIFICATION_FAILED = "verification_failed"


class Navigator:
    def __init__(self, sensors_data, persisted_state=None):
        self.step_size = 2  # TODO Determine if this is necessary here
        self.tolerance = 0.1  # TODO Determine if this is necessary here

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

    def send_light_command(self, pan_move, tilt_move, use_degrees=False):
        self.eos.set_pan(1, self.pan, pan_move, "r1", use_degrees)
        self.eos.set_tilt(1, self.tilt, tilt_move, "r1", use_degrees)
        self.pan += pan_move
        self.tilt += tilt_move

    def exploratory_phase(self):
        pan_min, pan_max = self.eos.get_pan_range("r1")
        tilt_min, tilt_max = self.eos.get_tilt_range("r1")

        # Start with no tilt (0) and tilt down (toward tilt_min) as we go
        give_up_tilt = 85
        search_tilt_max = 0
        search_tilt_min = tilt_min

        pan_step = 10.0
        tilt_step = 5.0
        threshold = 0.2

        if self.target_sensor is None:
            self.target_sensor = 1

        if self.previous_intensity == -1:
            self.previous_intensity = self.sensors_data[self.target_sensor]

        if not hasattr(self, "scan_pan"):
            self.scan_pan = pan_min
        if not hasattr(self, "scan_tilt"):
            self.scan_tilt = search_tilt_max

        # Keep track of pan direction
        if not hasattr(self, "pan_direction"):
            self.pan_direction = 1

        self.eos.set_pan(1, 0, self.scan_pan, "r1", use_degrees=True)
        self.eos.set_tilt(1, 0, self.scan_tilt, "r1", use_degrees=True)
        self.pan = self.scan_pan
        self.tilt = self.scan_tilt

        current_intensity = self.sensors_data[self.target_sensor]

        print(f"Current intensity of sensor {self.target_sensor}: {current_intensity}")

        if current_intensity > self.previous_intensity + threshold:
            return Phase.DIRECTED

        # Move pan
        self.scan_pan += pan_step * self.pan_direction

        if self.pan_direction == 1 and self.scan_pan > pan_max:
            self.scan_pan = pan_max
            self.pan_direction = -1
            self.scan_tilt -= tilt_step
            if self.scan_tilt < search_tilt_min:
                # Done scanning
                pass
        elif self.pan_direction == -1 and self.scan_pan < pan_min:
            self.scan_pan = pan_min
            self.pan_direction = 1
            self.scan_tilt -= tilt_step
            if self.scan_tilt < search_tilt_min:
                # Done scanning
                pass

        if abs(self.scan_tilt) >= give_up_tilt:
            # give up
            self.eos.set_pan(1, 0, 0, "r1", use_degrees=True)
            self.eos.set_tilt(1, 0, 0, "r1", use_degrees=True)
            self.eos.set_intensity(1, 0)
            return Phase.EXPLORATORY_FAILED

        return Phase.EXPLORATORY

    def directed_phase(self):
        # TODO: Implement directed phase
        return Phase.DIRECTED

    def verification_phase(self):
        # TODO: Implement verification phase
        return Phase.COMPLETE

    def detect_significant_change(self):
        # TODO: Implement detect_significant_change
        return False

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
