# Black Box User's Manual

## Theory of Operation
The "black box" takes a number of sensor inputs, performs processing and then outputs a range of analogue outputs suitable for connecting to a data acquisition system (DAS).

A load cell measuring torque is connected to an ADS1100 I2C analogue-to-digital converter interfaced with the Raspberry Pi Pico which then scales the reading to a 0-2.2Nm torque value.

A load cell measuring thrust is connected to a HX711 wheatstone bridge amplifier again interfaced with the Raspberry Pi Pico. The reading is scaled to 0-49N thrust value.

Revolutions per minute are sensed by a photoreflective sensor, with an analogue voltage then produced by the Raspberry Pi Pico that corresponds 0-5V at 0-10,000RPM.

Torque & thrust measurements along with a frame counter are emitted at 20Hz over a 3.3V UART connection to the DAS.

## System block diagram

![Block diagram of system functional components](block_diagram.svg)

## Board connection
1. Attach motor to front of torque measurement arm using appropriate mounting hardware (NOTE: the mounting holes are tapped to accept M3 mounting hardware)
2. Attach propellor under test to the motor using appropriate mounting hardware
3. Connect ESC motor wires to motor
4. Connect the ESC to XT60 female connector J5 (marked "POWER OUT")
5. Connect the thrust load cell (4-pin Molex KK connector) to J1 (marked "LOAD CELL")
6. Connect the torque load cell (3-pin Molex KK connector) to J6 (marked "TORQUE")
7. Connect the photoreflective sensor (4-pin Molex KK connector) to J3 (marked "TACHO")
8. Plug the DAS breakout cable (male DB-15 connector) into J2
9. Wire the DAS as required
10. Connect power to XT60 male connector J4 (marked "POWER IN")

## Board initialisation
Once the board is suitably wired and power applied, a zeroing cycle needs to be performed.

- Zero status is indicated by the green LED marked D7. When not illuminated, zeroing needs to be perfomed (see below)

Zeroing mostly applies the the load cell used to measure torque as due to environmental changes and sensor noise the zero point can drift slightly. It also serves to set the correct offset for the thrust load cell, accounting for any mass present.

To zero the system, press button "SW1" located in the south-east corner of the board.

The zero cycle takes around one second to complete, where a number of sensor readings are taken, averaged and then offsets applied as necessary. Once the cycle has complete, the green LED D7 should illuminate.

During operation (i.e. with an experimental cycle being run) the LED should remain illuminated. Upon returning to zero throttle the LED may begin to blink - this is the board running an automatic zeroing procedure as the zero may have drifted (equivalent to pressing the button). __Wait to run the next experimental cycle until the LED remains steadily lit!__

During zeroing, the UART output will pause (the frame counter will not increment during this time) as the firmware waits in a loop to average sensor readings. Once complete, the output will resume.

## Debug data
The USB port located on the Raspberry Pi Pico exposes a serial port when plugged into a computer. This outputs a line format that contains the raw counts from the ADC, HX711, torque force, calculated torque and thrust and the calculated photoreflector frequency (times this value by 60 to get motor RPM). An additional "CAL" status is present, this reflects whether the board has had first zeroing performed.

An example of the line format is `ADCV 0.513V, HX711 -206, TQF -0.00N, TQ -0.000Nm, THR 0.000N, TACHO 0.0Hz, CAL True`

## Firmware explanation
Firmware for the black box is written in MicroPython to lower the barrier to entry for modifications and understanding of the code.

The firmware has one external dependency on the `hx711-pico-mpy` library sourced from [here](https://github.com/endail/hx711-pico-mpy).

Hardware utilised by the firmware include the I2C, PWM, UART, timer and PIO peripherals.

A timer running at 20Hz fires an interrupt that calls `uart_timer_callback`. This is the function that increments the frame counter and emits a data frame over the UART.

A pin interrupt watches for a falling edge on the photoreflector tachometer input, calculates a difference in microseconds between interrupts and then a frequency which directly corresponds to the motor RPM.

A `while True` loop forms the main program loop. This repeatedly reads  both the ADC & HX711, performs smoothing on both (in the case of the HX711 a simple moving average is taken which slows the load cell response) and then calculates torque and thrust.

A scaling is applied to the tacho frequency value that scales from zero to the upper frequency limit (calculated in the code) to arbitrary PWM units and then outputs this value for low-pass filtering.

An `if` statement performs automatic zeroing by watching for a negative torque value and then calling the `zero_sensors` function.

Another `if` statement performs automatic zeroing by watching for the raw reading from the HX711 wandering outside a specified window. Sometimes this can occur if the torque sensor is calibrated and the HX711 returns a bogus value at the same time.