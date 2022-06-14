# Class to decode a rotary encoder and update a value. 
# You can update the value when you need it by calling update() with an intcapa or intcapb value.
# When callbacks are available you will be able to configure a callback which will be called whenever the value changes.
# Adapted from https://github.com/nstansby/rpi-rotary-encoder-python

class Encoder:
	def __init__(self, leftPin: int, rightPin: int, btnPin: int): # , callback: function = None
		self.leftPin = leftPin
		self.rightPin = rightPin
		self.btnPin = btnPin
		self.value = self.orig = int(0)
		self.button = int(1)
		self._state = str("00")
		self._direction = str("X")
		# self.callback = callback

	def update(self, intcap: 'list[int]') -> None:
		self.button = intcap[self.btnPin]
		oldState = self._state
		newState = "{}{}".format(intcap[self.rightPin], intcap[self.leftPin])
		dir = self._direction
		val = self.value
		# cal = self.callback
		if oldState == "00": # Resting position
			if newState == "01": # Turned right 1
				dir = "R"
			elif newState == "10": # Turned left 1
				dir = "L"
		elif oldState == "01": # R1 or L3 position
			if newState == "11": # Turned right 1
				dir = "R"
			elif newState == "00": # Turned left 1
				if dir == "L":
					val = val - 1
					# if cal is not None:
					# 	cal(val, dir)
		elif oldState == "10": # R3 or L1
			if newState == "11": # Turned left 1
				dir = "L"
			elif newState == "00": # Turned right 1
				if dir == "R":
					val = val + 1
					# if cal is not None:
					# 	cal(val, dir)
		else: # oldState == "11"
			if newState == "01": # Turned left 1
				dir = "L"
			elif newState == "10": # Turned right 1
				dir = "R"
			elif newState == "00": # Skipped an intermediate 01 or 10 state, but if we know direction then a turn is complete
				if dir == "L":
					val = val - 1
					# if cal is not None:
					# 	cal(val, dir)
				elif dir == "R":
					val = val + 1
					# if cal is not None:
					# 	cal(val, dir)		
		self._direction = dir
		self.value = val
		self._state = newState
		# self.callback = cal
