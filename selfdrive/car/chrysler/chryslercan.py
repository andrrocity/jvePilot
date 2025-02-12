from cereal import car
from selfdrive.car import make_can_msg


GearShifter = car.CarState.GearShifter
VisualAlert = car.CarControl.HUDControl.VisualAlert

def create_lkas_hud(packer, gear, lkas_active, hud_alert, hud_count, lkas_car_model):
  # LKAS_HUD 0x2a6 (678) Controls what lane-keeping icon is displayed.

  if hud_alert == VisualAlert.steerRequired:
    msg = b'\x00\x00\x00\x03\x00\x00\x00\x00'
    return make_can_msg(0x2a6, msg, 0)

  color = 1  # default values are for park or neutral in 2017 are 0 0, but trying 1 1 for 2019
  lines = 1
  alerts = 0

  if hud_count < (1 * 4):  # first 3 seconds, 4Hz
    alerts = 1
  # CAR.PACIFICA_2018_HYBRID and CAR.PACIFICA_2019_HYBRID
  # had color = 1 and lines = 1 but trying 2017 hybrid style for now.
  if gear in (GearShifter.drive, GearShifter.reverse, GearShifter.low):
    if lkas_active:
      color = 3  # 1 is white, 2 is green, 3 is active
      lines = 6  # 1 is , 2 is left white, 3 is right white, 4 is left over line, 5 is left over line, 6 is both white, 7 is left active
      # 8 is left active as well, 9 is right active, 10 is also right active, 11 is left over line, 12 is right over line
    else:
      color = 1  # display white.
      lines = 1

  values = {
    "LKAS_ICON_COLOR": color,  # byte 0, last 2 bits
    "CAR_MODEL": lkas_car_model,  # byte 1
    "LKAS_LANE_LINES": lines,  # byte 2, last 4 bits
    "LKAS_ALERTS": alerts,  # byte 3, last 4 bits
    }

  return packer.make_can_msg("LKAS_HUD", 0, values)  # 0x2a6


def create_lkas_command(packer, apply_steer, moving_fast, frame):
  # LKAS_COMMAND 0x292 (658) Lane-keeping signal to turn the wheel.
  values = {
    "LKAS_STEERING_TORQUE": apply_steer,
    "LKAS_HIGH_TORQUE": int(moving_fast),
    "COUNTER": frame,
  }
  return packer.make_can_msg("LKAS_COMMAND", 0, values)

def create_wheel_buttons_command(cc, packer, frame, button, value):
  # WHEEL_BUTTONS (571) Message sent
  values = {
    button: value,
    "COUNTER": frame,
  }
  return packer.make_can_msg("WHEEL_BUTTONS", 0, values)
