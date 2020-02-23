from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
from datetime import datetime
import serial
from time import sleep
from utils import buzzer, rand_str_gen

import string, random

from multiprocessing import Process

host = "" # <replace> with your AWS Endpoint
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

callb_msgpayload = {}

# Custom MQTT message callback
def customCallback(client, userdata, message):
    global callb_msgpayload
    callb_msgpayload = json.loads(message.payload)

# ---------------------------------------------------------#

# gets motion and light value from Arduino
def arduinoData():
    ser = serial.Serial("/dev/ttyUSB0", 9600) # open serial port
    # ser.baudrate = 9600
    data = ser.readline() # light value and motion value
    return data

def sendMotionLight():
    monicam_rpi = AWSIoTMQTTClient("monicamMQTT_pub" + rand_str_gen())
    monicam_rpi.configureEndpoint(host, 8883)
    monicam_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    monicam_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    monicam_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    monicam_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    monicam_rpi.configureMQTTOperationTimeout(5)  # 5 sec
    monicam_rpi.connect()
    while True:
        data = arduinoData().split(",")
        # print(data)
        lightValue = data[0]
        motionValue = data[1].strip()
        # lightValue = 404
        # motionValue = 1
        date_time = str(datetime.now().replace(microsecond=0)).replace(" ", "_")
        message = {}
        message["deviceid"] = "monicam"
        message["datetimeid"] = date_time
        message["lightvalue"] = lightValue
        message["motionvalue"] = motionValue
        print(message)
        monicam_rpi.publish("sensors/lightmotionvalue" , json.dumps(message), 1)


def main():
    sendMotionLight_proc = Process(name='sendMotionLight', target=sendMotionLight)
    sendMotionLight_proc.start()
    sendMotionLight_proc.join()

if __name__ == '__main__':
    main()
