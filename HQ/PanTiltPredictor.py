import numpy as np
from scipy.optimize import minimize

class PanTiltPredictor:
    def __init__(self, four_points):
        """
        Initialize the predictor with four reference points.

        Parameters:
        - four_points: List of four tuples, each containing:
            (x_i, y_i, pan_i, tilt_i)
            where:
                x_i, y_i: Coordinates of the point on stage in feet (float)
                pan_i: Pan angle in degrees (0-360)
                tilt_i: Tilt angle in degrees (0-90)
        """
        if len(four_points) != 4:
            raise ValueError("Exactly four reference points are required.")

        self.four_points = four_points
        self.light_position = self._find_light_position()

    @staticmethod
    def _normalize_angle(angle):
        """Normalize angle to be within [0, 360) degrees."""
        return angle % 360

    @staticmethod
    def _angle_difference(a1, a2):
        """
        Compute the minimal difference between two angles.

        Parameters:
        - a1, a2: Angles in degrees.

        Returns:
        - Minimal absolute difference in degrees.
        """
        diff = np.abs(a1 - a2) % 360
        return min(diff, 360 - diff)

    @staticmethod
    def _compute_pan_tilt(Lx, Ly, h, x, y):
        """
        Compute pan and tilt angles from light position to a target point.

        Parameters:
        - Lx, Ly, h: Coordinates of the light.
        - x, y: Coordinates of the target point.

        Returns:
        - pan: Pan angle in degrees (0-360).
        - tilt: Tilt angle in degrees (0-90).
        """
        dx = x - Lx
        dy = y - Ly
        distance = np.sqrt(dx**2 + dy**2)

        # Compute pan using arctan2, result in degrees [0, 360)
        pan = np.degrees(np.arctan2(dy, dx)) % 360

        # Compute tilt using arctan (distance / height), result in degrees [0, 90]
        tilt = np.degrees(np.arctan(distance / h))

        return pan, tilt

    def _find_light_position(self):
        """
        Determine the light's position (Lx, Ly, h) using the four reference points.

        Returns:
        - Tuple containing (Lx, Ly, h) in feet.
        """
        def error_function(params):
            Lx, Ly, h = params
            total_error = 0
            for (x, y, pan_obs, tilt_obs) in self.four_points:
                pan_calc, tilt_calc = self._compute_pan_tilt(Lx, Ly, h, x, y)
                pan_diff = self._angle_difference(pan_calc, pan_obs)
                tilt_diff = tilt_calc - tilt_obs
                # Accumulate squared differences
                total_error += pan_diff**2 + tilt_diff**2
            return total_error

        # Initial guess: center of the stage and an arbitrary height
        x_coords = [p[0] for p in self.four_points]
        y_coords = [p[1] for p in self.four_points]
        initial_Lx = (max(x_coords) + min(x_coords)) / 2
        initial_Ly = (max(y_coords) + min(y_coords)) / 2
        initial_h = 10.0  # Initial guess for height in feet

        initial_guess = [initial_Lx, initial_Ly, initial_h]

        # Perform optimization to minimize the error function
        result = minimize(
            error_function,
            initial_guess,
            method='Nelder-Mead',
            options={'xtol': 1e-6, 'ftol': 1e-6, 'maxiter': 10000}
        )

        if result.success:
            Lx, Ly, h = result.x
            if h <= 0:
                raise ValueError("Computed height is non-positive. Please check the input data.")
            return Lx, Ly, h
        else:
            raise RuntimeError("Optimization failed to determine the light position.")

    def predict_pan_tilt(self, x, y):
        """
        Predict the pan and tilt angles for a given (x, y) point.

        Parameters:
        - x, y: Coordinates of the target point in feet.

        Returns:
        - Tuple containing:
            (pan in degrees [0-360], tilt in degrees [0-90])
        """
        Lx, Ly, h = self.light_position
        pan, tilt = self._compute_pan_tilt(Lx, Ly, h, x, y)
        return pan, tilt

    def get_light_position(self):
        """
        Get the determined position of the light.

        Returns:
        - Tuple containing (Lx, Ly, h) in feet.
        """
        return self.light_position

# -------------------- Example Usage --------------------

def feet_inches_to_feet(feet, inches):
    """
    Convert feet and inches to decimal feet.

    Parameters:
    - feet: Feet component (int or float).
    - inches: Inches component (int or float).

    Returns:
    - Total feet as a float.
    """
    return feet + inches / 12.0
