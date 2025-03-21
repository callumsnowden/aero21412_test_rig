import math
from machine import Pin, I2C, PWM, UART, Timer
from time import ticks_us, sleep
from src.hx711 import *

'''
AERO21412 "Black Box" MicroPython firmware
v0.1 12/2024

Dependencies:
hx711-pico-mpy https://github.com/endail/hx711-pico-mpy
    - Copy entire "src" folder to the Pico, then delete "__init.py__"
'''

# Functions
def calculate_moving_average(new_data_point, data_list, average_size):
    # Add fresh data
    data_list.insert(0, new_data_point)
    try:
        # Remove nth item in list
        data_list.pop(average_size)
    except Exception as e:
        pass
    total = 0
    total = sum(data_list)
        
    value = math.ceil(total / len(data_list))
    if(value == None):
        return 0
    else:
        return value

def calc_time(p):
    global last_tacho_time, tacho_freq
    entry_ticks_us = ticks_us()
    time_delta = entry_ticks_us - last_tacho_time
    tacho_freq = float(1.0 / (time_delta / 1000000))
    last_tacho_time = entry_ticks_us
    
def zero_sensors(p, hx711_handle):
    global thrust_zero_value, torque_zero_value, LED_STATE
    torque_avg = []
    thrust_avg = 0
    thrust_averaging_window = 10
    thrust_raw_values = []
    
    # Take an average of readings
    for x in range(0, 10):
        hx_val = hx711_handle.get_value()
        thrust_avg = calculate_moving_average(hx_val, thrust_raw_values, thrust_averaging_window)
        
        raw_adc_data = i2c.readfrom(ads1100_addr, 3)
        adc_voltage = (5.0/16384) * ((raw_adc_data[0] << 8) | raw_adc_data[1])
        torque_avg.append(adc_voltage)
        
        sleep(0.05)
    
    torque_zero_value = sum(torque_avg) / len(torque_avg)
    thrust_zero_value = thrust_avg
    LED_STATE = True
    
def num_to_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax
        - outMin))

def uart_timer_callback(t):
    global frame_id, thrust, torque
    if frame_id == 1000:
        frame_id = 0
        
    # Emit packet over UART
    data_uart.write("<{0:03},{1:0>2.3f},{2:0>2.3f}>".format(frame_id, thrust, torque))
    frame_id = frame_id + 1

# GPIO configuration
scl_pin = Pin(9)
sda_pin = Pin(8)
hx_clk_pin = Pin(6)
hx_data_pin = Pin(7)
led_pin = Pin(16, mode=Pin.OUT)
button_pin = Pin(2, mode=Pin.IN)
tacho_in_pin = Pin(3, mode=Pin.IN)
tacho_pwm_pin = Pin(4)
uart_tx = Pin(0)
uart_rx = Pin(1)

tacho_in_pin.irq(handler=calc_time, trigger=Pin.IRQ_FALLING)

tacho_pwm = PWM(tacho_pwm_pin, freq=100000, duty_u16=0) # Init PWM at 100kHz, no duty to start
data_uart = UART(0, baudrate=115200, tx=uart_tx, rx=uart_rx)

# ADS1100 configuration
ads1100_addr = 0x4B
ads1100_conf = 0x08

# Misc. variables
adc_vcc_const = 4.85 # 5V voltage, measured on board
last_tacho_time = 0 # Used for interrupt timing
tacho_freq = 0.0 # Calculated frequency based on interrupt timing
torque_zero_value = 0 # Stored when zero button is pressed
thrust_zero_value = 0 # Stored when zero button is pressed
raw_adc_data = [] # Buffer for data from I2C ADC
max_rpm = 25000 # Maximum expected input RPM
max_frequency = (max_rpm / 60) # Calculated, used as top of map value for PWM output
torque_arm_length = 50 # Length from motor centre point to load cell, in mm

# Final variables sent over UART
thrust = 0
torque = 0
frame_id = 0

LED_STATE = False

global hx
# Configure HX711 (clock 6, data 7)
hx = hx711(hx_clk_pin, hx_data_pin)
hx.set_power(hx711.power.pwr_up)
hx.set_gain(hx711.gain.gain_128)
hx.set_power(hx711.power.pwr_down)
hx.wait_power_down()
hx.set_power(hx711.power.pwr_up)
hx.wait_settle(hx711.rate.rate_80)

# Configure I2C
i2c = I2C(0, scl=scl_pin, sda=sda_pin, freq=100000)

# Configure ADC for 16sps, 1x PGA
i2c.writeto(ads1100_addr, int.to_bytes(ads1100_conf))

def main():
    global adc_voltage, hx_val, torque_zero_value, thrust_zero_value, LED_STATE, thrust, torque, frame_id
    
    thrust_raw_values = []
    thrust_averaging_window = 15
    
    '''
    Important to update this per board!
    1. Monitor the USB UART debug output
    2. Zero the scale (some zero point variation is expected, can be safely ignored assuming a range of +/- 100 counts)
    3. Add a known mass and then take note of the "HX711" value on the debug output
    4. Calculate const = loaded count / mass (N)
    '''
    thrust_scale_const = 86006.493
    
    # Establish a timer to ensure 20Hz UART data rate
    uart_timer = Timer(period=50, mode=Timer.PERIODIC, callback=uart_timer_callback)
    
    while True:
        if button_pin.value() == 0:
            zero_sensors(None, hx)
            hx_val = calculate_moving_average(hx.get_value(), thrust_raw_values, thrust_averaging_window)
            hx_val = hx_val - thrust_zero_value
            
            if hx_val < -50 or hx_val > 50:
                # Re-run calibration, occasionally the HX711 cal gets screwy
                zero_sensors(None, hx)

        # Read HX711 value
        hx_val = calculate_moving_average(hx.get_value(), thrust_raw_values, thrust_averaging_window)
        hx_val = hx_val - thrust_zero_value
        
        # Calculate force on thrust load cell
        thrust = abs(round(hx_val / thrust_scale_const, 3))
        
        # Convert ADC reading into voltage - ignore any negative swing in the readings (ADC is pseudo-differential)
        raw_adc_data = i2c.readfrom(ads1100_addr, 3)
        adc_voltage = round((5.0/16384) * ((raw_adc_data[0] << 8) | raw_adc_data[1]), 3)
        
        # Map ADC voltage directly to a force in N (44.39N value is calculated from 4.53kgf * 9.8 where 4.53 is the maximum the load cell can measure)
        torque_force = round(num_to_range(adc_voltage, torque_zero_value, 4.50, 0, 44.39), 2)
        
        # If we have a negative torque value then calibrate - load cell has been unloaded and zero point has drifted slightly
        if torque_force < 0:
            torque_force = 0
            LED_STATE = False
            led_pin.value(LED_STATE)
            zero_sensors(None, hx)
        
        # Calculate actual torque from arm length and measured force
        torque = torque_force * (torque_arm_length / 1000)
        
        # Scale tacho frequency to PWM range and update
        tacho_pwm.duty_u16(int(num_to_range(tacho_freq, 0, max_frequency, 0, 65535)))

        # Quickly calculate RPM for debugging purposes
        motor_rpm = tacho_freq * 60
        
        # Debug printing to USB serial interface
        print("ADCV {}V, HX711 {}, TQF {:0>2.2f}N, TQ {:0>2.3f}Nm, THR {:0>2.3f}N, TACHO {:0>2.1f} RPM, CAL {}".format(adc_voltage, hx_val, torque_force, torque, thrust, motor_rpm, LED_STATE))
        
        led_pin.value(LED_STATE)

if __name__ == "__main__":
    main()