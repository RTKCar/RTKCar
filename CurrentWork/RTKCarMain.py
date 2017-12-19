import queue
import socket
import threading
import select
import sys
import serial
import logging

ser = serial.Serial(
    port='/dev/serial0',
    baudrate=500000,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=None
)

logger = logging.getLogger('test') #Create a log with the same name as the script that created it
logger.setLevel(logging.DEBUG)
#Create handlers and set their logging level
filehandler_dbg = logging.FileHandler(logger.name + '-debug.log', mode='w')
filehandler_dbg.setLevel(logging.DEBUG)
#Create custom formats of the logrecord fit for both the logfile and the console
streamformatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s') #We only want to see certain parts of the message
#Apply formatters to handlers
filehandler_dbg.setFormatter(streamformatter)
#Add handlers to logger
logger.addHandler(filehandler_dbg)

host = '172.20.10.5'
port = 8888
buffer_size = 1024

styrvinkel_max_hoger = 60
styrvinkel_max_vanster = 120
current_angle = 90

car_start = '6:4:0:0:0:0:0:0:0\n'
car_stop = '6:2:0:0:0:0:0:0:0\n'


send_queue = queue.Queue()
receive_queue = queue.Queue()
stop_queue = queue.Queue(1)
handle_sensor = queue.Queue()
serial_out = queue.Queue()
handle_data = queue.Queue()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(0)


def serial_handler():
    while True:
        readable, writable, _ = select.select([ser], [ser], [])
        for read in readable:
            if read is ser:
                data = ser.read()
                logger.info('Serial in: %s' % data)
                handle_sensor.put(data)
        for write in writable:
            if write is ser:
                if serial_out.qsize() > 0:
                    data = serial_out.get()
                    logger.info('Serial out: %s' % data)
                    ser.write(data.encode())


def process_sensor_data():
    while True:
        if handle_sensor.qsize() > 0:
            information = handle_sensor.get()
            index = [0, 1, 2, 3]
            can_id, left, middle, right = [information[i] for i in index]
            if str(can_id) == '15':
                logger.info('Sensor data: %s' % information)
                print("Sensor data med id 15: " + str(information))

                if 1 <= int(left) < 20 or 1 <= int(middle) < 20 or 1 <= int(right) < 20:
                    if int(left) < int(middle) and int(left) < int(right):
                        send_queue.put('ObjectDetected,' + str(left))
                    elif int(middle) < int(left) and int(middle) < int(right):
                        send_queue.put('ObjectDetected,' + str(middle))
                    elif int(right) < int(middle) and int(right) < int(left):
                        send_queue.put('ObjectDetected,' + str(right))
                    # Skicka via socket "ObjectDetected,Avstand"
                    serial_out.put(car_stop)
                    logger.info('Car will stop')
                    stop_queue.put(1)
                elif stop_queue.qsize() < 1:
                    serial_out.put(car_start)
                    logger.info('Car will start')
                    stop_queue.get()


def pi_client():
    connected = False
    while not connected:
        try:
            sock.connect((host, port))

            connected = True
        except Exception as e:
            pass
    while True:
        readable, writable, error = select.select([sock], [sock], [sock])
        for read in readable:
            if read is sock:
                if stop_queue.qsize() == 0:
                    data = sock.recv(1024).decode('utf-8')
                    logger.info('Server data in: %s' % data)
                    handle_data.put(data)
        for write in writable:
            if write is sock:
                if send_queue.qsize() > 0:
                    data = send_queue.get()
                    logger.info('Server data out: %s' % data)
                    sock.send(data.encode('utf-8'))


def handledata():
    while True:
        global current_angle
        if handle_data.qsize() > 0:
            theString = handle_data.get()
            logger.info('Data to be handled: %s' % theString)
            tempString = theString.split(':')
            if tempString[0] == '6':
                serial_out.put(theString + '\n')
            elif tempString[0] == '10':
                serial_out.put(theString + '\n')
            elif tempString[0] == 'w' or tempString[0] == 'w\n':
                serial_out.put('6:4:0:0:0:0:0:0:0\n')
            elif tempString[0] == 's' or tempString[0] == 's\n':
                serial_out.put('6:2:0:0:0:0:0:0:0\n')
            elif tempString[0] == 'd' or tempString[0] == 'd\n':
                if current_angle > styrvinkel_max_hoger:
                    current_angle -= 2
                    serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')
            elif tempString[0] == 'a' or tempString[0] == 'a\n':
                if current_angle < styrvinkel_max_vanster:
                    current_angle += 2
                    serial_out.put('10:' + str(current_angle) + ':0:0:0:0:0:0:0\n')


if __name__ == '__main__':
    serial_han = threading.Thread(target=serial_handler)
    pi = threading.Thread(target=pi_client)
    sendata = threading.Thread(target=process_sensor_data)
    handata = threading.Thread(target=handledata)
    serial_han.daemon = True
    sendata.daemon = True
    pi.daemon = True
    handata.daemon = True
    handata.start()
    serial_han.start()
    sendata.start()
    pi.start()

    while True:
        pass
