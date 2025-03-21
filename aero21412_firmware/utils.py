import math
from machine import Pin, PWM

'''
AERO21412 utility & test functions
'''

max_rpm = 25000 # Used for scaling function
max_frequency = (max_rpm / 60) # Calculated, used as top of map value for PWM output

# Pins
tacho_pwm_pin = Pin(4)
led_pin = Pin(16, mode=Pin.OUT)
button_pin = Pin(2, mode=Pin.IN)
tacho_pwm = PWM(tacho_pwm_pin, freq=100000, duty_u16=0) # Init PWM at 100kHz, no duty to start

def num_to_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax
        - outMin))

def ledon():
	led_pin.value(1)

def ledoff():
	led_pin.value(0)

def emitspeed(rpm):
	tacho_freq = rpm / 60
	tacho_pwm.duty_u16(int(num_to_range(tacho_freq, 0, max_frequency, 0, 65535)))