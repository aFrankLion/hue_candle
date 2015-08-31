"""Control Philips Hue Lights to simulate a candle flickering."""

__author__ = 'Adam Tart'

import json
import random
import requests
import sys
import time

# Whether to send commands to Philips Hue lights (True) or just print debug
# info to stdout (False).
SEND_TO_HUE = True
# Whether all lights should follow the same flicker pattern (True) or have
# their own each (False).
IN_SYNC = True
# IDs of lights to use in simulation. These can be retrieved by visiting
# http://<bridge_ip>/api/<username>/lights
LIGHTS = [2, 4]
# Maximum brightness lights should reach, in [0, 255].
MAX_BRIGHTNESS = 220
# Minimum brightness lights should reach, in [0, 255].
MIN_BRIGHTNESS = 100

# Recommendation is 10 API calls per light per second, so this *should* be
# 0.1 or higher, going as low as 1 millisecond hasn't seemed to cause
# problems.
TRANSITION_TIME = 0.005  # seconds


def GetBridgeIpAndUsername(filename):
  """Retrieves Hue Bridge IP address and username from file.
  
  File should be two lines, first line containing the IP address of the
  bridge, and second line containing the username, e.g.:
  
      192.168.1.42
      ab8d8fbd8d8d8bdbd88d8bd80898
  
  See http://www.developers.meethue.com/documentation/getting-started
  
  Args:
    filename: string, filename containing bridge IP and username.
  
  Returns:
    Tuple (string, string): (<bridge_ip>, <username>).
  """
  with open(filename, 'r') as f:
    lines = [line.strip() for line in f.readlines()]
  if len(lines) != 2:
    raise ValueError('File must have two lines!')
  return (lines[0], lines[1])


class Flame(object):
  """Represents a candle flame."""

  WIND_VARIABILITY = 2
  FLAME_AGILITY = 20
  # Baseline target to which wind will constantly try to approach, in [0, 255].
  WIND_BASELINE = 5

  def __init__(self):
    # Variables should be in range [0, 255].
    # Raw brightness of flame
    self.flame = MAX_BRIGHTNESS
    # Filtered brightness of flame to simulate inertia
    self.flameprime = MAX_BRIGHTNESS
    # Wind strength
    self.wind = self.WIND_BASELINE

  def GetNextFlameBrightness(self):
    """Get the next brightness value to set light to.

    Attempts to simulate a candle flicker using phyiscally-inspired candle
    simulation: Flame gets brighter and brighter until it reaches max
    brightness, except random gusts of wind will try to set flame to a random
    brightness. Flame will slowly transition to that random brightness to
    simulate inertia.

    Algorithm inspired by:
      https://github.com/EternityForest/CandleFlickerSimulator/

    Returns:
      Integer between MIN_BRIGHTNESS and MAX_BRIGHTNESS, inclusive.
    """
    # Simulate a gust of wind by potentially setting the wind var to a random
    # value.
    if random.randint(0, 1000) < self.WIND_VARIABILITY:
      self.wind = random.randint(0, 255)

    # The wind constantly settles towards its baseline value.
    if self.wind > self.WIND_BASELINE:
      self.wind -= 1

    # The flame constantly gets brighter until the wind knocks it down.
    if self.flame < MAX_BRIGHTNESS:
      self.flame += 1

    # Depending on the wind strength, potentially set the flame brightness to a
    # random value.
    if random.randint(0, 255) < self.wind:
      self.flame = random.randint(MIN_BRIGHTNESS, MAX_BRIGHTNESS)

    # Real flames look like they have inertia, so instead of just setting the
    # flame brightness to the new value of self.flame, the value should
    # instead gradually approach the new brightness (where that rate is
    # determined by FLAME_AGILITY).
    if self.flame > self.flameprime:
      self.flameprime = min(
          self.flameprime + self.FLAME_AGILITY,
          MAX_BRIGHTNESS
      )
    else:
      self.flameprime = max(
          self.flameprime - self.FLAME_AGILITY,
          MIN_BRIGHTNESS
      )
    # No need to handle the case when flame == flameprime, as the resulting
    # jittering from that case just adds to the realism.

    return self.flameprime


def main():
  bridge_ip, username = GetBridgeIpAndUsername('./bridge_ip_and_username.txt')
  # Turn on lights.
  if SEND_TO_HUE:
    for i in LIGHTS:
      url = 'http://%s/api/%s/lights/%d/state' % (bridge_ip, username, i)
      body = {
          'on': True,
      }
      r = requests.put(url, data=json.dumps(body))
      if r.status_code != 200:
        print r.status_code
        print r.text

  # Create a Flame for each light.
  flames = {}
  for i in LIGHTS:
    flame = Flame()
    flames[i] = flame
  # Infinite loop to constantly update light brightness.
  while True:
    if SEND_TO_HUE:
      if IN_SYNC:
        brightness = flames[LIGHTS[0]].GetNextFlameBrightness()
      for i in LIGHTS:
        if not IN_SYNC:
          brightness = flames[i].GetNextFlameBrightness()
        url = 'http://%s/api/%s/lights/%d/state' % (bridge_ip, username, i)
        body = {
            'bri': brightness,
            'transitiontime': int(TRANSITION_TIME * 1000)
        }
        r = requests.put(url, data=json.dumps(body))
        if r.status_code != 200:
          print r.status_code
          print r.text
    else:
      # Useful for debugging purposes: print string of characters to stdout.
      brightness = flames[LIGHTS[0]].GetNextFlameBrightness()
      width = 51.0
      percent = int(width * brightness / MAX_BRIGHTNESS)
      line = ''.join([
          ' ' * int((width - percent)/2),
          '-' * percent,
          ' ' * int((width - percent)/2)
      ])
      sys.stdout.write('{}\r'.format(line))
      sys.stdout.flush()
    time.sleep(TRANSITION_TIME)


if __name__ == '__main__':
  main()
