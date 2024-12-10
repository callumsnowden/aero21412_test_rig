# aero21412_test_rig
AERO21412 Avionics Coursework 1 – Wind Tunnel Test Rig "Black Box"

## Description
A "black box" PCB that provides the interface between a number of sensors on the wind tunnel test rig and an external data acquisition system.The aim is to provide a number of outputs measuring supply voltage and current; motor torque, thrust and rotational speed. A PWM input signal should be provided that is passed directly to the ESC module.

## Signals to/from DAS
- [] RPM as voltage with scaling factor
- [] Scaled supply voltage
- [] Supply current as voltage with scaling factor
- [] UART for force measurements (optional control input)

## UART measurement packet specification

`<AAA,BB.BBB,CC.CCC>`

Measurements are transmitted at 20 Hz. The packet consists of a start character of `<` followed by an incrementing three-digit frame identifier `AAA`. After this follows a three decimal place measurement of thrust in Newtons `BB.BBB` and then a three decimal place measurement of torque in Newton metres `CC.CCC`. An end character `>` terminates the packet.

## Hardware

A Raspberry Pi Pico (RP2040) handles interfacing the load cells and photointerruptor and is responsible for transmitting UART messages plus generating an analogue voltage representing RPM.

### Sensors

- One load cell for thrust measurement (Siemens 7MH5102-1PD00) with a rated load of 5kg
- One load cell (analogue voltage output) for torque measurement (TE Connectivity FC2231-0000-0010-L) with a rated load of 10lbf (13.5 Nm) and a voltage output of 0.5-4.5V
- Photointerruptor for RPM measurement