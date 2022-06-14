# ContRoller
A (basis for a) MIDI Swiss Army Knife running on a microcontroller.

The main perk is that it can provide rather stable MIDI Clock.

Initially developed on and tested with the Adafruit Feather M4 Express board.
Other required hardware includes:
- ssd1306 OLED display
- mcp23017 I2C GPIO expander
- MB85RC256V 256Kbit/32KByte FRAM

The code requires CircuitPython.
For all modules to be available and to run fast, you might need to compile CircuitPython with custom settings (no worries, it's easy).

__PLEASE NOTE: This is not mature code. You are free to use it, contribute with feedback or
pull requests, but don't expect that every issue will be fixed in an urgent manner, because they won't.__
