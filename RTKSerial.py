import serial
import time

# RTKSerial is a class that hold the information of the serial port RX/TX
# var running 1 = you can send messages to the CANBuss, 0 it's blocked and 2 is you are running the car manually
#
class RTKSerial(object):
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=500000,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0.05
    )
    running = 1
    stop = 0
    srvMsg = ''

# Styrsystem 10
# SensorSystem 15
# Huvudenhet 5
# Drivsystem 6
#
