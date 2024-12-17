from PanTiltPredictor import PanTiltPredictor

def feet_inches_to_feet(feet, inches):
    return feet + inches/12

# reference_point1 = (pos_x, pos_y, pan, tilt)
def predict(target_x, target_y, reference_point1: tuple, reference_point2: tuple, reference_point3: tuple, reference_point4: tuple):
    predictor = PanTiltPredictor([reference_point1, reference_point2, reference_point3, reference_point4])

    pan, tilt = predictor.predict_pan_tilt(target_x, target_y)
    return pan, tilt


def convert_360_to_nearest_pan(current_pan, new_pan, range):
    if not 0 <= new_pan <= 360:
        raise ValueError(f"Pan value {pan} is out of range (0 to 360)")

    range_min, range_max = range

    if not range_min <= new_pan <= range_max:
        raise ValueError(f"Pan value {pan} is out of range ({min} to {max})")

    candidates = [new_pan, new_pan + 360, new_pan - 360]

    closest = min(candidates, key=lambda x: abs(x - current_pan))

    # ensure the closest value is within the range
    if not range_min <= closest <= range_max:
        raise ValueError(f"Pan value {closest} is out of range ({min} to {max})")

    return closest
def convert_360_to_light_pan(new_pan, current_pan):
    """
    Converts a pan value from 0-360 back into the range -270 to 270,
    choosing the closest equivalent based on the current pan value.

    Parameters:
        new_pan (float): The new pan value in the range 0-360.
        current_pan (float): The current pan value in the range -270 to 270.

    Returns:
        float: The closest pan value in the range -270 to 270.
    """
    if not 0 <= new_pan <= 360:
        raise ValueError(f"New pan value {new_pan} must be in the range 0-360.")

    # Generate candidates mapped into the light's range (-270 to 270)
    candidates = [
        new_pan,            # As is
        new_pan - 360       # Wrap around into negative range
    ]

    # Normalize candidates into -270 to 270 range
    normalized_candidates = [((c + 270) % 540) - 270 for c in candidates]

    # Return the closest candidate to the current_pan
    closest_pan = min(normalized_candidates, key=lambda x: abs(x - current_pan))
    return closest_pan


def main():
    reference_point1 = (feet_inches_to_feet(0, 0), feet_inches_to_feet(0, 0), -222.28835, 50)
    reference_point2 = (feet_inches_to_feet(20, 0), feet_inches_to_feet(0, 0), 45.354528, 48)
    reference_point3 = (feet_inches_to_feet(0, 0), feet_inches_to_feet(15, 0), 218.31935, 50)
    reference_point4 = (feet_inches_to_feet(20, 0), feet_inches_to_feet(15, 0), -39.759313999999996, 46)

    target_x = feet_inches_to_feet(10, 0)
    target_y = feet_inches_to_feet(7.5, 0)

    pan, tilt = predict(target_x, target_y, reference_point1, reference_point2, reference_point3, reference_point4)
    print(f"Pan: {pan}, Tilt: {tilt}")
    print(f"Pan: {pan}, Tilt: {tilt}")

if __name__ == "__main__":
    main()
