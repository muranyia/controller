import asyncio
# import countio
import time
from random import randint
import math
import board
import busio
import bitbangio
import terminalio
#import neopixel
import digitalio
import analogio
# import rotaryio
import displayio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_displayio_ssd1306
from adafruit_mcp230xx.mcp23017 import MCP23017        # mcp23017 I2C GPIO expander
import adafruit_fram                                   # MB85RC256V 256Kbit/32KByte FRAM
import adafruit_midi
from adafruit_midi import MIDI
from adafruit_midi.midi_message     import MIDIMessage
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.program_change   import ProgramChange
from adafruit_midi.system_exclusive import SystemExclusive
from adafruit_midi.timing_clock     import TimingClock
from adafruit_midi.start            import Start
from adafruit_midi.midi_continue    import Continue
from adafruit_midi.stop             import Stop
#import usb_host
#import usb
#import usb.util
#import foamyguy_nvm_helper as nvm_helper
from encoder import Encoder
import sys
#import traceback
import gc
#import circuitpython_schedule as schedule
import microcontroller
import micropython
from micropython import const
# try:
#     import typing
# except ImportError:
#     pass
import alarm
import supervisor

supervisor.disable_autoreload()

displayio.release_displays()

#  setup screen
class Screen():
	@micropython.native
	def __init__(self, display: adafruit_displayio_ssd1306.SSD1306, settings: 'list[list[Setting]]'):
		cur_top_val = settings[0][1].val
		cur_sub_val = settings[cur_top_val][0].val
		white = const(0xFFFFFF)
		screen = displayio.Group()
		display.show(screen)
		lilfont = bitmap_font.load_font("neep-iso8859-1-05x11.bdf") # terminalio.FONT
		lilfont.load_glyphs(b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ .-&¼½¢£¤¥¦§')              # type: ignore
		midfont = bitmap_font.load_font("neep-iso8859-1-10x20.bdf")
		midfont.load_glyphs(b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ ')                        # type: ignore
		bigfont = bitmap_font.load_font("AsapCondensed-Bold-30.bdf")
		bigfont.load_glyphs(b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ .-&¼½¢£¤¥¦§')              # type: ignore
		screen_title = label.Label(midfont, text=settings[0][1].vals[cur_top_val], color=white, x=0, y=5)
		screen.append(screen_title)
		self.title = screen_title
		screen_subtitle = label.Label(midfont, text=settings[cur_top_val][cur_sub_val].name, color=white, x=0, y=26)
		screen.append(screen_subtitle)
		self.subtitle = screen_subtitle
		if len(settings[cur_top_val][cur_sub_val].vals)>0:
			screen_main = label.Label(bigfont, text=str(settings[cur_top_val][cur_sub_val].vals[settings[cur_top_val][cur_sub_val].val]), color=white, x=0, y=50)
		else:
			screen_main = label.Label(bigfont, text=str(settings[cur_top_val][cur_sub_val].val), color=white, x=0, y=50) # text=str('{:06.2f}'.format(settings[cur_top_val][cur_sub_val].val)) for float
		screen.append(screen_main)
		self.value = screen_main
		screen_indicator_labels = displayio.Group(x=60, y=3)
		screen_indicator_LFO1_label = label.Label(lilfont, text="LFO1", color=white, x=0, y=0)
		screen_indicator_labels.append(screen_indicator_LFO1_label)
		screen_indicator_LFO2_label = label.Label(lilfont, text="LFO2", color=white, x=0, y=9)
		screen_indicator_labels.append(screen_indicator_LFO2_label)
		screen_indicator_CONV_label = label.Label(lilfont, text="CONV", color=white, x=0, y=18)
		screen_indicator_labels.append(screen_indicator_CONV_label)
		screen_indicator_bpm_label = label.Label(lilfont, text=" INT", color=white, x=0, y=27)
		screen_indicator_labels.append(screen_indicator_bpm_label)
		screen.append(screen_indicator_labels)   
		screen_indicators = displayio.Group(x=84, y=3)
		screen_indicator_LFO1 = label.Label(lilfont, text=str('{:02.0f}'.format(settings[2][1].val)) + "-" + str('{:03.0f}'.format(settings[2][2].val)) + "-" + str(settings[2][3].vals[settings[2][3].val]) + str(settings[2][4].vals[settings[2][4].val]), color=white, x=0, y=0)
		screen_indicators.append(screen_indicator_LFO1)
		self.lfo1 = screen_indicator_LFO1
		screen_indicator_LFO2 = label.Label(lilfont, text=str('{:02.0f}'.format(settings[3][1].val)) + "-" + str('{:03.0f}'.format(settings[3][2].val)) + "-" + str(settings[3][3].vals[settings[3][3].val]) + str(settings[3][4].vals[settings[3][4].val]), color=white, x=0, y=9)
		screen_indicators.append(screen_indicator_LFO2)
		self.lfo2 = screen_indicator_LFO2
		screen_indicator_CONV = label.Label(lilfont, text="---", color=white, x=0, y=18)
		screen_indicators.append(screen_indicator_CONV)
		self.conv = screen_indicator_CONV
		screen_indicator_bpm = label.Label(lilfont, text=str(settings[1][2].val) + "bpm", color=white, x=0, y=27) # text=str('{:06.2f}'.format(settings[1][2].val)) for float
		screen_indicators.append(screen_indicator_bpm)
		self.bpm = screen_indicator_bpm
		screen.append(screen_indicators)
		print("Screen set up.")

#  cycle through range of values
def cycle_range(current_value: int, delta_value: int, range_min: int, range_max: int) -> int:
	return ((current_value-range_min+delta_value)%(range_max-range_min+1))+range_min

#  invert label colors
def invert_colors(object) -> None:
	bgcolor = object.background_color or 0x000000
	object.background_color = object.color
	object.color = bgcolor

#  find value text
def value_text(cur_top_val: int, cur_sub_val: int, cur_val: int, settings: 'list[list[Setting]]') -> str:
	cur_setting = settings[cur_top_val][cur_sub_val]
	try:
		valslen = len(cur_setting.vals)
	except TypeError:
		valslen = 0
	except IndexError:
		print("Wrong index: ", str(cur_top_val), " ", str(cur_sub_val))
		return("---")
	#return(cur_setting.vals[cur_val] if valslen>0 else str('{:06.2f}'.format(cur_val)) if cur_setting.dec>0 else str(cur_val)) # TODO: handle how many decimals
	return(cur_setting.vals[cur_val] if valslen>0 else str(cur_val))


#  change 1st level menu
async def change_topmenu(delta: int, screen: displayio.Group, settings: 'list[list[Setting]]') -> None:
	cur_top_val = cycle_range(settings[0][1].val, delta, 1, len(settings)-1)
	cur_sub_val = settings[cur_top_val][0].val
	cur_setting = settings[cur_top_val][cur_sub_val]
	cur_val = cur_setting.val
	screen.title.text = settings[0][1].vals[cur_top_val]
	screen.subtitle.text = cur_setting.name
	screen.value.text = value_text(cur_top_val, cur_sub_val, cur_val, settings)
	settings[0][1].val = cur_top_val # store selected main menu

#  change 2nd level menu
async def change_submenu(delta: int, screen: displayio.Group, settings: 'list[list[Setting]]') -> None:
	cur_top_val = settings[0][1].val
	cur_sub_val = cycle_range(settings[cur_top_val][0].val, delta, 1, len(settings[cur_top_val])-1)
	cur_setting = settings[cur_top_val][cur_sub_val]
	cur_val = cur_setting.val
	screen.title.text = settings[0][1].vals[cur_top_val]
	screen.subtitle.text = cur_setting.name
	screen.value.text = value_text(cur_top_val, cur_sub_val, cur_val, settings)
	settings[cur_top_val][0].val = cur_sub_val # store selected submenu

#  change value
@micropython.native
async def change_value(delta: int, screen: displayio.Group, settings: 'list[list[Setting]]') -> None:
	# TODO: this is slow. Burn font into firmware via mpconfigboard.mk
	cur_top_val = int(settings[0][1].val)
	cur_sub_val = int(settings[cur_top_val][0].val)
	cur_setting = settings[cur_top_val][cur_sub_val]
	cur_val     = int(0)
	if cur_setting.cyc == True:
		cur_val = cycle_range(cur_setting.val, delta, cur_setting.min, cur_setting.max)
	else:
		cur_val = min(max(cur_setting.val + delta, cur_setting.min), cur_setting.max)
	#screen.title.text = settings[0][1].vals[cur_top_val] + ": " + cur_setting.name
	screen.value.text = value_text(cur_top_val, cur_sub_val, cur_val, settings)
	settings[cur_top_val][cur_sub_val].val = cur_val # store new value
	# Update indicators
	if cur_top_val == 1:
		screen.bpm.text  = str(settings[1][2].val) + "bpm" # TODO: plus divider, source; str('{:06.2f}'.format(settings[1][2].val)) for float
	elif cur_top_val == 2:
		screen.lfo1.text = str('{:02.0f}'.format(settings[2][1].val)) + "-" + str('{:03.0f}'.format(settings[2][2].val)) + "-" + str(settings[2][3].vals[settings[2][3].val]) + str(settings[2][4].vals[settings[2][4].val])
	elif cur_top_val == 3:
		screen.lfo2.text = str('{:02.0f}'.format(settings[3][2].val)) + "-" + str('{:03.0f}'.format(settings[3][2].val)) + "-" + str(settings[3][3].vals[settings[3][3].val]) + str(settings[3][4].vals[settings[3][4].val])

#  handle value changes that are not MIDI related
async def fire_value(delta: int, screen: displayio.Group, settings: 'list[list[Setting]]', display: adafruit_displayio_ssd1306.SSD1306) -> None:
	cur_top_val = int(settings[0][1].val)
	cur_sub_val = int(settings[cur_top_val][0].val)
	if (cur_top_val, cur_sub_val) == (5, 1): # display brightness
		display.brightness = settings[cur_top_val][cur_sub_val].val/10

#  catch and trigger handling interrupts on pins - pins, mcp, encoders, midiuart, screen, display, running_state, running_start, settings
@micropython.native
async def catch_interrupts(pins: 'list[microcontroller.Pin]', midiuart: adafruit_midi.MIDI, screen: displayio.Group, display: adafruit_displayio_ssd1306.SSD1306, running_state: 'dict[str, bool]', running_start: 'dict[str, float]', nvram: adafruit_fram.FRAM_I2C, settings: 'list[list[Setting]]') -> None:
	#  setup for GPIO expander
	mcp = MCP23017(i2c, address=0x20) # Default is 0x20 (A0, A1, A2 all grounded).
	mcp.iodir = mcp.gppu = mcp.interrupt_enable = 0xFFFF # 0xFF00 enable interrupts on port B pins (switches) only
	mcp.interrupt_configuration = 0x0000  # compare pins against previous values
	mcp.clear_ints()
	#  setup of encoders and buttons
	encoders = []
	encoders.append(Encoder(0, 1, 2))  # GPA0, GPA1, GPA2, D5
	encoders.append(Encoder(3, 4, 5))  # GPA3, GPA4, GPA5, D5
	encoders.append(Encoder(0, 1, 2))  # GPB0, GPB1, GPB2, D6
	#  setup for interrupt pins
	mcp_inta = digitalio.DigitalInOut(pins[0])
	mcp_inta.switch_to_input(pull=digitalio.Pull.UP)
	mcp_intb = digitalio.DigitalInOut(pins[1])
	mcp_intb.switch_to_input(pull=digitalio.Pull.UP)

	intcapa = [int(0)] * 8
	cur_top_val = int(0)
	#cur_sub_val = int(0)
	delta = int(0)
	enc1_presstime = float(0)

	while True:
		if not mcp_inta.value:
			intcapa = mcp.int_capa # This will also clear inta
			encoders[0].update(intcapa)
			encoders[1].update(intcapa)
			cur_top_val = int(settings[0][1].val)
			#cur_sub_val = int(settings[cur_top_val][0].val)
			# rotation
			if encoders[0].value != encoders[0].orig:
				await change_topmenu(encoders[0].value - encoders[0].orig, screen, settings)
				encoders[0].orig = encoders[0].value

			if encoders[1].value != encoders[1].orig:
				await change_submenu(encoders[1].value - encoders[1].orig, screen, settings)
				encoders[1].orig = encoders[1].value

			if encoders[0].button == 0: # 1st button press: clock
				enc1_presstime = time.monotonic()
				if running_state["clock"] == False:
					running_state["clock"] = True
					running_start["clock"] = time.monotonic()
					midiuart.send(Start())
				else:
					running_state["clock"] = False
					running_start["clock"] = 0
					midiuart.send(Stop())
			elif encoders[0].button == 1 and enc1_presstime != 0 and (time.monotonic() - enc1_presstime) > 2: # 1st button long press release: go to deep sleep (= switch off)
				print("ContRoller shutting down...")
				#save_changed_settings(nvram, settings)
				display.sleep()
				mcp_inta.deinit()
				# Only the following pins can be configured for tamper input IN0:PB00; IN1:PB02; IN2:PA02; IN3:PC00; IN4:PC01 There's also OUT:PB01 but haven't checked 
				alarm.exit_and_deep_sleep_until_alarms(alarm.pin.PinAlarm(pin=pins[0], value=False, pull=True)) # 
			else:
				enc1_presstime = 0
			
			if   encoders[1].button == 0 and cur_top_val == 2: # 2nd button press: lfo's
				running_state["lfo1"] = True if not running_state["lfo1"] else False
			elif encoders[1].button == 0 and cur_top_val == 3:
				running_state["lfo2"] = True if not running_state["lfo2"] else False

		if not mcp_intb.value:
			encoders[2].update(mcp.int_capb) # This will also clear intb
			if encoders[2].value != encoders[2].orig:
				# delta = (encoders[2].value - encoders[2].orig)/10 if settings[cur_top_val][cur_sub_val].dec > 0 and encoders[2].button == 0 else encoders[2].value - encoders[2].orig # TODO: handle more than 1 decimal
				delta = encoders[2].value - encoders[2].orig
				await change_value(delta, screen, settings)
				await fire_value(delta, screen, settings, display)
				encoders[2].orig = encoders[2].value

		await asyncio.sleep(0.01)

#  setup single setting
# class Setting:
# 	def __new__(cls, val: int, dec: int = 0, name: str = "", min: int = 0, max: int = 127, cyc: bool = True, vals: 'list[str]' = []):
# 		obj = object.__new__(cls)
# 		obj.val  = val
# 		obj.dec  = dec
# 		obj.name = name
# 		obj.min  = min
# 		obj.max  = max
# 		obj.cyc  = cyc # True: cycle through values, False: stop at min and max
# 		obj.vals = vals
# 		obj.addr = int(-1)
# 		obj.size = int(0)
# 		return obj
# 	def __getitem__(self, key):
# 		return getattr(self, key)
# 	def __setitem__(self, key, val):
# 		return setattr(self, key, val)

class Setting:
	def __init__(self, val: int, dec: int = 0, name: str = "", min: int = 0, max: int = 127, cyc: bool = True, vals: 'list[str]' = []):
		self.val  = val
		self.dec  = dec
		self.name = name
		self.min  = min
		self.max  = max
		self.cyc  = cyc # True: cycle through values, False: stop at min and max
		self.vals = vals
		self.addr = int(-1) # ????????????????
		self.size = int(0) # ????????????????
	# def __getitem__(self, key):
	# 	return getattr(self, key)
	# def __setitem__(self, key, val):
	# 	return setattr(self, key, val)


#  read all settings
def read_all_settings(nvram: adafruit_fram.FRAM_I2C, configlist: 'list[list[Setting]]') -> 'list[list[Setting]]':
	length = int(sum( [ len(topmenu) for topmenu in configlist]))
	if nvram[0] == length:
		nvram_content = nvram[0:length]
		pos = int(0)
		for tidx, topmenu in enumerate(configlist):
			for sidx, submenu in enumerate(topmenu):
				val = nvram_content[pos]
				if val >= configlist[tidx][sidx].min and val <= configlist[tidx][sidx].max:
					configlist[tidx][sidx].val = val
				else:
					print("Saved config value for [", str(tidx), "][", str(sidx), "] is out of range, using default value instead.")
				pos += 1
	else:
		print("Length of settings changed, won't read saved settings.")
	return configlist

#  save all settings
def save_all_settings(nvram: adafruit_fram.FRAM_I2C, configlist: 'list[list[Setting]]') -> None:
	len = int(0)
	state_content = bytearray()
	for tidx, topmenu in enumerate(configlist):
		for sidx, submenu in enumerate(topmenu):
			state_content.append(configlist[tidx][sidx].val)
			len += 1
	state_content[0] = len # overwriting first byte with the current length
	nvram[0:len] = state_content # assuming that nvram length is enough

#  save changed settings loop
async def save_all_settings_loop(nvram: adafruit_fram.FRAM_I2C, settings: 'list[list[Setting]]') -> None:
	while True:
		save_all_settings(nvram, settings)
		await asyncio.sleep(5) # Save every 5 seconds

#  read MIDI
@micropython.native
async def read_uart_midi(midiport: MIDI, midi_read_buffer: 'list[MIDIMessage]') -> None:
	while True:
		res = midiport.receive()
		if isinstance(res, MIDIMessage):
			midi_read_buffer.append(res)
		await asyncio.sleep(0)

#  process midi
@micropython.native
async def process_midi(midiport: adafruit_midi.MIDI, blinkport: digitalio.DigitalInOut, midi_read_buffer: 'list[MIDIMessage]', midi_send_buffer: 'list[MIDIMessage]', screen: displayio.Group, running_state: 'dict[str, bool]', running_start: 'dict[str, float]', settings: 'list[list[Setting]]') -> None:
	lastc = float(0)
	now   = float(0)
	msg   = MIDIMessage()
	count = int(0)
	bpms  = []
	while True:
		#  filter incoming MIDI
		if len(midi_read_buffer) > 0:
			msg = midi_read_buffer.pop(0)
			print(type(msg))
			if isinstance(msg, (TimingClock, Start, Stop, Continue)):
				if settings[1][1].val == 1:
					# send it out immediately
					midiport.send(msg)
					if isinstance(msg, TimingClock):
						# calculate BPM and update screen
						now = time.monotonic()
						if lastc != 0:
							bpms.append(int(2.5 / ( now - lastc )))
							if len(bpms) > 96: bpms.pop(0)
							screen.bpm.text  = str(int(sum(bpms) / len(bpms))) + "bpm" # TODO: average the last few
							count = count + 1
							if   count == 20:
								blinkport.value = False 
							elif count == 24:
								blinkport.value = True
								count = 0
						lastc = now
				else:
					lastc = 0
					count = 0
					bpms  = []
			elif isinstance(msg, (NoteOn, NoteOff)):
				if settings[4][1].val == 1:
					midi_send_buffer.append(msg)
			elif isinstance(msg, ControlChange):
				if settings[4][2].val == 1:
					midi_send_buffer.append(msg) # TODO: limit rate
			elif isinstance(msg, ProgramChange):
				if settings[4][3].val == 1:
					midi_send_buffer.append(msg)
			elif isinstance(msg, SystemExclusive):
				if settings[4][4].val == 1:
					midi_send_buffer.append(msg)
		await asyncio.sleep(0.001)

#  calculate lfo's
@micropython.native
async def calculate_lfos(midi_send_buffer: 'list[MIDIMessage]', running_state: 'dict[str, bool]', running_start: 'dict[str, float]', settings: 'list[list[Setting]]') -> None:
	lfo1_old = lfo2_old = lfo1_new = lfo2_new = int(0)
	bpm      = int(settings[1][2].val)
	bar      = float(240 / bpm) # length of one bar in seconds
	nextb    = float(running_start["clock"] + bar)
	while True:
		if running_state["lfo1"] == True or running_state["lfo2"] == True:
			bpm = int(settings[1][2].val)
			bar = float(240 / bpm)
			run = float(time.monotonic() - running_start["clock"]) # run time of midi clock
			inb = float(( run / bar) % 1)
			inb_= float((-run / bar) % 1)
			len1= float([0.25, 0.5, 1, 2, 4, 8][settings[2][3].val])
			len2= float([0.25, 0.5, 1, 2, 4, 8][settings[3][3].val])
			# TODO: apply len

		if running_state["lfo1"] == True:
			# LFO1 Shapes: Tri, Saw1, Saw2, Sin, Squ, S&H
			if settings[2][4].val == 0:   # Triangle /\ 
				if inb <= 0.5:
					lfo1_new = math.floor(inb * 254)
				else:
					lfo1_new = math.floor(inb_* 254)
			elif settings[2][4].val == 1: # Saw 1 /|
				lfo1_new = math.floor(inb * 127)
			elif settings[2][4].val == 2: # Saw 2 |\
				lfo1_new = math.floor(inb_* 127)
			elif settings[2][4].val == 3: # Sine 
				lfo1_new = math.floor(( (math.sin(run / bar) + 1 ) / 2 ) * 127) # ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min
			elif settings[2][4].val == 4: # Square
				if inb <= 0.5:
					lfo1_new = int(0)
				else:
					lfo1_new = int(127)
			elif settings[2][4].val == 5 and time.monotonic() >= nextb: # Sample & Hold
				lfo1_new = randint(0, 127)
			if math.fabs(lfo1_new - lfo1_old) >= 1:
				# print("1:", lfo1_new)
				midi_send_buffer.append(ControlChange(control=settings[2][2].val, value=lfo1_new, channel=settings[2][1].val))
				lfo1_old = lfo1_new
		if running_state["lfo2"] == True:
			# LFO2 Shapes: Tri, Saw1, Saw2, Sin, Squ, S&H
			if settings[3][4].val == 0:   # Triangle /\ 
				if inb <= 0.5:
					lfo2_new = math.floor(inb * 254)
				else:
					lfo2_new = math.floor(inb_* 254)
			elif settings[3][4].val == 1: # Saw 1 /|
				lfo2_new = math.floor(inb * 127)
			elif settings[3][4].val == 2: # Saw 2 |\
				lfo2_new = math.floor(inb_* 127)
			elif settings[3][4].val == 3: # Sine 
				lfo2_new = math.floor(( (math.sin(run / bar) + 1 ) / 2 ) * 127) # ( (old_value - old_min) / (old_max - old_min) ) * (new_max - new_min) + new_min
			elif settings[3][4].val == 4: # Square
				if inb <= 0.5:
					lfo2_new = int(0)
				else:
					lfo2_new = int(127)
			elif settings[3][4].val == 5 and time.monotonic() >= nextb: # Sample & Hold
				lfo2_new = randint(0, 127)
			if math.fabs(lfo2_new - lfo2_old) >= 1:
				# print("2:", lfo2_new)
				midi_send_buffer.append(ControlChange(control=settings[3][2].val, value=lfo2_new, channel=settings[3][1].val))
				lfo2_old = lfo2_new
		if time.monotonic() >= nextb:
			nextb = nextb + bar	
		await asyncio.sleep(0.02)

#  send MIDI
async def send_uart_midi(midiport: MIDI, midi_send_buffer: 'list[MIDIMessage]') -> None:
	while True:
		if len(midi_send_buffer) > 0:
			midiport.send(midi_send_buffer.pop(0))
		await asyncio.sleep(0)

#  send MIDI clock
@micropython.native
async def send_uart_midi_clock(midiport: MIDI, blinkport: digitalio.DigitalInOut, settings: 'list[list[Setting]]') -> None:
	bpm   = int(settings[1][2].val)
	mul   = float([0.25, 0.5, 1, 2, 4, 8][settings[1][3].val])
	late  = float(0)
	next  = float(time.monotonic() + ( 2.5 / ( bpm * mul ) )) # ( 60 / ( bpm * 24 * mul ) ) = 2.5 / ( bpm * mul )
	count = int(0)
	# TODO: check if we skipped some ticks
	while True:
		bpm = int(settings[1][2].val)
		mul = float([0.25, 0.5, 1, 2, 4, 8][settings[1][3].val])
		if settings[1][1].val == 0:
			if time.monotonic() >= next:
				midiport.send(TimingClock())
				late = float(time.monotonic() - next)
				if ( late / ( 2.5 / ( bpm * mul )) ) > 10:
					print("Clock delay:", str(late), "s")
				count = count + 1
				if   count == 20:
					blinkport.value = False 
				elif count == 24:
					blinkport.value = True
					count = 0
				next = next + ( 2.5 / ( bpm * mul ) )
		else:
			next = time.monotonic() + ( 2.5 / ( bpm * mul ) )
		await asyncio.sleep(0)

#  check battery voltage
async def check_battery(nvram: adafruit_fram.FRAM_I2C, settings: 'list[list[Setting]]') -> None:
	vbat = analogio.AnalogIn(board.VOLTAGE_MONITOR)
	while True:
		battery_voltage = float((vbat.value * 3.3) / 65536 * 2)
		if battery_voltage < 3.3:
			print("BATTERY LOW: {:.2f} V".format(battery_voltage))
		elif battery_voltage < 3: # TODO: Save and shutdown
				print("ContRoller shutting down...")
				save_all_settings(nvram, settings)
				displayio.release_displays()
				try:
					spi.unlock()
					print("SPI unlocked.")
				except:
					pass
				try:
					i2c.unlock()
					print("I2C unlocked.")
				except:
					pass
				print("ContRoller Ended.")
				sys.exit(0)
		await asyncio.sleep(30)

#  cleanup routine
async def cleanup() -> None:
	while True:
		gc.collect()
		await asyncio.sleep(1)

#  dummy asyncio task
async def foo() -> None:
	while True:
		await asyncio.sleep(0)

#  i2c scanning (for debugging)
def scani2c(i2c: busio.I2C) -> None:
		while not i2c.try_lock():
			pass
		try:
			while True:
				print(
					"I2C addresses found:",
					[hex(device_address) for device_address in i2c.scan()],
				)
				time.sleep(1)
		finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
			i2c.unlock()

#  main loop
async def main():
	"""
	UART MIDI (DIN):   TX,    RX
	USB HOST:            -,  D12
	I2C:               SCL,  SDA
	SPI:         SCK, MOSI, MISO
	mcp23017 INT A, B:  A0,   A1
	"""

	print("ContRoller Starting.")

	# if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
	# 	pass

	# TODO: alarm.sleep_nvram for state saving?

	#  setup for FT232RL USB-to-TTL converter (driver is for FT232H?)
	#dev = usb.core.find(idVendor=0x0403, idProduct=0x6001)
	#print(dev)

	#  turn off on-board neopixel
	# pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0)
	# pixel.fill((0, 0, 0))

	#  setup for MIDI UART [Note: On the Trinket M0, if you are using both UART and I2C, you must create the UART object first]
	# midi = MIDI(midi_out=usb_midi.ports[1], out_channel=0)                                     # USB (built-in port) MIDI
	mu1 = busio.UART(tx=board.TX, rx=board.RX, baudrate=31250, timeout=0.001)
	midiuart = MIDI(midi_in=mu1, midi_out=mu1, in_buf_size=128) # DIN UART MIDI
	mu2 = busio.UART(tx=board.D13, rx=board.D12, baudrate=115200, timeout=0.001)
	midihost = MIDI(midi_in=mu2, midi_out=mu2, in_buf_size=128) # USB Host UART MIDI ----- TODO: MIDI out

	#  setup for USB Host (for MIDI)
	#usbhost = usb_host.Port(dp=board.A2, dm=board.A3)

	#  setup I2C for SSD1306 OLED, mcp23017 GPIO, EEPROM
	global i2c
	i2c   = busio.I2C(board.SCL, board.SDA, frequency=17000000)
	
	#  setup SPI for SD1306 OLED
	global spi
	#spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
	spi = board.SPI()

	#  setup for OLED
	# displaybus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=board.D9)
	displaybus = displayio.FourWire(spi_bus=spi, command=board.D10, chip_select=board.D11, reset=board.D9, baudrate=8000000) # , polarity=1, phase=1
	display = adafruit_displayio_ssd1306.SSD1306(displaybus, width=128, height=64)

	#  setup for EEPROM
	# nvram = adafruit_24lc32.EEPROM_I2C(i2c_bus=i2c, address=0x50)
	# print("EEPROM length: {} bytes".format(len(nvram)))

	#  setup for FRAM
	#  default ddress 0x50
	nvram = adafruit_fram.FRAM_I2C(i2c)
	print("FRAM length: {} bytes".format(len(nvram)))

	#  create menu structure and data model
	settings = read_all_settings(nvram, [
		[
			Setting(val=0,   dec=0, name="ByteLength"),
			Setting(val=1,   dec=0, name="TopMenu",   min=1,  max=4,   vals=[ "SYSTEM", "CLOCK", "LFO1", "LFO2", "CONV", "SETUP" ])
		],
		[
			Setting(val=2,   dec=0, name="CurrentItem"),
			Setting(val=0,   dec=0, name="SRC",       min=0,  max=2,   vals=[ "INT", "DIN", "USB" ]),
			Setting(val=133, dec=2, name="OUT",       min=20, max=255, cyc=False),                                       # TODO: The decimal value has to be applied
			Setting(val=2,   dec=0, name="MULTI",     min=0,  max=5,   vals=["¼", "½", "1", "2", "4", "8"]) # (¼½1248)
		],
		[
			Setting(val=1,   dec=0, name="CurrentItem"),
			Setting(val=0,   dec=0, name="CHAN",      min=0, max=15,   vals=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"], cyc=False),
			Setting(val=74,  dec=0, name="CC",        min=1, max=95), # vals...
			Setting(val=2,   dec=0, name="LEN",       min=0, max=5,    vals=["¼", "½", "1", "2", "4", "8"]),
			Setting(val=0,   dec=0, name="SHAPE",     min=0, max=5,    vals=["¢", "£", "¤", "¥", "¦", "§"]) # Tri, Saw1, Saw2, Sin, Squ, S&H (¢£¤¥¦)
		],
		[
			Setting(val=1,   dec=0, name="CurrentItem"),
			Setting(val=0,   dec=0, name="CHAN",      min=0, max=15,   vals=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"], cyc=False),
			Setting(val=74,  dec=0, name="CC",        min=1, max=95), # vals...
			Setting(val=2,   dec=0, name="LEN",       min=0, max=5,    vals=["¼", "½", "1", "2", "4", "8"]),
			Setting(val=0,   dec=0, name="SHAPE",     min=0, max=5,    vals=["¢", "£", "¤", "¥", "¦", "§"]) # Tri, Saw1, Saw2, Sin, Squ, S&H (¢£¤¥¦)
		],
		[
			Setting(val=1,   dec=0, name="CurrentItem"),
			Setting(val=0,   dec=0, name="NOTE",       min=0, max=1,   vals=[ "OFF", "THRU" ]),
			Setting(val=0,   dec=0, name="CC",         min=0, max=1,   vals=[ "OFF", "THRU" ]),
			Setting(val=0,   dec=0, name="PRGC",       min=0, max=1,   vals=[ "OFF", "THRU" ]),
			Setting(val=0,   dec=0, name="SYSEX",      min=0, max=1,   vals=[ "OFF", "THRU" ])
		],
		[
			Setting(val=1,   dec=0, name="CurrentItem"),
			Setting(val=5,   dec=0, name="LIGHT",      min=0, max=10,   cyc=False) # To be divided by 10
		]
	])

	#  create the displayio screen
	screen = Screen(display, settings)

	#  create midi message buffers
	midi_send_buffer = []
	midi_read_buffer = []
	#  running states
	running_state = {"clock": False, "lfo1": True, "lfo2": False}
	running_start = {"clock": float(0)}

	#  setup LED lamp
	blinkport = digitalio.DigitalInOut(board.A4)
	blinkport.switch_to_output()

	print("ContRoller Started :o)")

	#asyncio.PriorityQueue ?
	# loop.call_soon?

	#  setup event loop
	await asyncio.gather(
	#	asyncio.create_task(foo()),
	 	asyncio.create_task(catch_interrupts([board.A0, board.A1], midiuart, screen, display, running_state, running_start, nvram, settings)),
		asyncio.create_task(send_uart_midi_clock(midiuart, blinkport, settings)),
	 	asyncio.create_task(read_uart_midi(midiuart, midi_read_buffer)),
	 	asyncio.create_task(read_uart_midi(midihost, midi_read_buffer)),
	 	asyncio.create_task(process_midi(midiuart, blinkport, midi_read_buffer, midi_send_buffer, screen, running_state, running_start, settings)),
		asyncio.create_task(calculate_lfos(midi_send_buffer, running_state, running_start, settings)),
	 	asyncio.create_task(save_all_settings_loop(nvram, settings)), # Enabling this will wear down the storage hardware quickly, except if it's FRAM
	 	asyncio.create_task(send_uart_midi(midiuart, midi_send_buffer)),
		asyncio.create_task(check_battery(nvram, settings)),
		asyncio.create_task(cleanup())
	)

try:
	asyncio.run(main())
except (KeyboardInterrupt, ValueError) as e: #
	# print("### ERROR ###")
	# print(traceback.format_exc())
	print(e)
	# print("#############")
	displayio.release_displays()
	try:
		spi.unlock()
		print("SPI unlocked.")
	except:
		pass
	try:
		i2c.unlock()
		print("I2C unlocked.")
	except:
		pass
	print("ContRoller Ended.")
	sys.exit(0)