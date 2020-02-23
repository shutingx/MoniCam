import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from utils import rand_str_gen, buzzer
from multiprocessing import Process
from time import sleep

host = "" # <replace> with your AWS Endpoint
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

def alarmCallback(client, userdata, message):
    print(message.payload)
    if (json.loads(message.payload)).get("alarm", 0) == 1:
        buzzer()

def getAlarmStat():
    monicam_rpi = AWSIoTMQTTClient("monicamMQTT_sub" + rand_str_gen())
    monicam_rpi.configureEndpoint(host, 8883)
    monicam_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    monicam_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    monicam_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    monicam_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    monicam_rpi.configureMQTTOperationTimeout(5)  # 5 sec
    monicam_rpi.connect()
    monicam_rpi.subscribe("api/alert/alarm", 1, alarmCallback)
    while True:
        print("Alarm detection in progress...")
        sleep(5)

if __name__ == '__main__':
    getAlarmStat_proc = Process(name='getAlarmStat', target=getAlarmStat)
    getAlarmStat_proc.start()
    getAlarmStat_proc.join()
