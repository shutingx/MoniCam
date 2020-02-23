import serial # for communication with arduino
import mysql.connector # for communication with phpmysql db
from time import sleep # for sleep (delay) function
import time # for timing operations
from datetime import datetime # for getting current date and time
import sys # for any system functions such as error msgs
import RPi.GPIO as GPIO # for operations requiring GPIO pins
import MFRC522 # for RFID reader
import signal # to capture keyboard interrupts
from gpiozero import Buzzer, MotionSensor, LED # for buzzer, motion sensor and led
from io import BytesIO # an object to hold image bytes
import os # for working with files and directories
import re # for working with regular expressions
from utils import camera, buzzer, lcd_display, rfid_reader, DynamoDB_class, rand_str_gen # for all the shared functions
from telegrambot import send_user_Msg # for sending user image msg
# for setting queries
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from boto3.dynamodb.conditions import Key, Attr
import boto, botocore, boto3
import json
from multiprocessing import Process
import serial
# declaring the LED GPIO pins
yellowLED = LED(20)
greenLED = LED(21)

deviceid = "monicam"
prog_run = False
################################################################################
# For communication with the server.py via MQTT

# Setting AWS endpoint and filepaths of CAs and key
host = "" # <replace> with your AWS Endpoint
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

callb_msgpayload = {} # global variable that stores the current callback message

# Custom MQTT message callback
def customCallback(client, userdata, message):
    global callb_msgpayload
    callb_msgpayload = json.loads(message.payload)
    # print("cust callback")
    # print(callb_msgpayload)

# ---------------------------------------------------------#

def publisher(topic, message):
    monicam_rpi = AWSIoTMQTTClient("monicamMQTT_pub" + rand_str_gen())
    monicam_rpi.configureEndpoint(host, 8883)
    monicam_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    monicam_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    monicam_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    monicam_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    monicam_rpi.configureMQTTOperationTimeout(5)  # 5 sec
    monicam_rpi.connect()
    monicam_rpi.publish(topic , json.dumps(message), 1)
    sleep(2)
    monicam_rpi.disconnect()

def subscriber(topic):
    monicam_rpi = AWSIoTMQTTClient("monicamMQTT_sub" + rand_str_gen())
    monicam_rpi.configureEndpoint(host, 8883)
    monicam_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    monicam_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    monicam_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
    monicam_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
    monicam_rpi.configureMQTTOperationTimeout(5)  # 5 sec
    monicam_rpi.connect()
    monicam_rpi.subscribe(topic, 1, customCallback)
    sleep(2)
    monicam_rpi.unsubscribe(topic)
    monicam_rpi.disconnect()
################################################################################
# The following chunk of code is for image recognition

dir_path = "/home/pi/motion_captures/"
# To store images to s3
def s3_imgstore(filepath):
    global img_bucket
    global dir_path
    # Create an S3 resource
    s3 = boto3.resource('s3', region_name='us-east-1')

    # Set the bucket name
    bucket = '' # <replace> with the bucket containing the attempts by people
    exists = True

    try:
        s3.meta.client.head_bucket(Bucket=bucket)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            exists = False

    if exists == False:
      s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={
        'LocationConstraint': 'us-east-1'})

    # Upload a new file
    s3.Object(bucket, filepath).put(Body=open(dir_path + filepath, 'rb'))
    print("File uploaded")

# Sends the request to AWS Rekognition to get the specified photos and then compare them to see if they match or not
def s3RekogniseFace(username, attempt_img):
    global img_bucket
    global dir_path
    client = boto3.client('rekognition', region_name='us-east-1')
    face_matched = False
    response = client.compare_faces(
        SimilarityThreshold=90,
        SourceImage={
            'S3Object': {
                'Bucket': '', # <replace> with the bucket containing your authenticated users' faces
                'Name': username + '.jpeg'
            }
        },
        TargetImage={
            'S3Object': {
                'Bucket': '', # <replace> with the bucket containing the attempts by people
                'Name': attempt_img
            }
        }
    )
    if (not response['FaceMatches']):
        face_matched = False
    else:
        face_matched = True
        for faceMatch in response['FaceMatches']:
            position = faceMatch['Face']['BoundingBox']
            similarity = str(faceMatch['Similarity'])
            print('The face at ' +
                   str(position['Left']) + ' ' +
                   str(position['Top']) +
                   ' matches with ' + username + ' with ' + similarity + '% confidence')

    return face_matched, response

################################################################################
# To control the led lighting
def ledControl(yellow, green):
    if 'off' in yellow:
        yellowLED.off()
    elif 'on' in yellow:
        yellowLED.on()

    if 'off' in green:
        greenLED.off()
    elif 'on' in green:
        greenLED.on()

##############################################################################

# for telegram alert
def telebotalert(command, data):
    print "sending telegram alert"
    send_user_Msg(command, data)

##############################################################################

# for logging the access attempt by publishing message to api/alert/attempt
def attempt_logger(attempt_img, date_time, rfid_id, username, success):
    print "logging attempt"
    if str(username).find('[]') != -1:
        username = ""
    message = {}
    message["deviceid"] = deviceid
    message["attempt_datetime"] = date_time
    message["rfid_id"] = rfid_id
    message["username"] = username
    message["success"] = success
    message["attempt_img_path"] = attempt_img
    publisher("api/alert/attempt", message)

# query for the existence of the rfid id
def query_rfid(rfid_id):
    print "querying rfid id"
    keycondexpress=Key('deviceid').eq(deviceid)
    db = DynamoDB_class()
    users = db.get_item("user_info", keycondexpress)
    user_rfid_id = ''
    username = None
    if users != None:
        for i in users:
            user_rfid_id = i.get('rfid_id', None)
            if user_rfid_id == rfid_id:
                username = i.get('username', None)
    return username

# check if rfid card is valid
def rfid_checker():
    global prog_run
    print "checking rfid\n"
    lcd_display(["Please present", "RFID card"])
    attempt = 0
    username = None
    success = 'No'
    date_time = ''
    attempt_img = ''
    while username == None or str(username).find('[]') != -1 or success == 'No':
        # check for number of attempts
        # if over 3 failed attempts ring buzzer
        if attempt < 4:
            attempt = attempt + 1
            rfid_id = rfid_reader()
            # call motion_sensor function if no card in 60 seconds
            if rfid_id == "timeout":
                print("rfid read timeout!")
                prog_run = False
                break
            else:
                date_time = str(datetime.now().replace(microsecond=0)).replace(" ", "_")
                username = query_rfid(rfid_id)
                print username
                if username == None or str(username).find('[]') != -1:
                    if attempt < 4:
                        lcd_display(["Please try", "again!"])
                else:
                    lcd_display(["Please wait.", "Scanning face."])
                    attempt_img = camera(date_time)
                    s3_imgstore(attempt_img)
                    sleep(10)
                    face_matched, response = s3RekogniseFace(username, attempt_img)
                    if face_matched:
                        success = 'Yes'
                        print("User " + username + " has authenticated successfully!")
                    else:
                        lcd_display(["Unauthorised", "User!"])
                        print("WARNING - UNAUTHORIZED USER is using " + username + "\'s card! ")
                        telebotalert("uauth_user", username)
                attempt_logger(attempt_img, date_time, rfid_id, username, success)
        elif attempt == 4:
            telebotalert("failed_attempts", '')
            lcd_display(["UNAUTHORIZED!", "ALERT TRIGGERED!"])
            buzzer() # make buzzer sound
            prog_run = False
            break
    print "username is => " + str(username)
    if success == 'Yes':
        ledControl('off', 'on')
        telebotalert("success", username)
        lcd_display(["Welcome home", str(username) + "!"])
        sleep(5)
        prog_run = False

# sends message to mqtt topic sensors/lightmotionvalimg
def add_motion_to_db(light_val, motion_sig, date_time):
    print "adding motion to db\n"
    motion_img = camera(date_time)
    message={
        "deviceid": deviceid,
        "motion_datetime": date_time,
        "lightvalue": light_val,
        "motionvalue": motion_sig,
        "motion_image": motion_img
    }
    publisher("sensors/lightmotionvalimg", message)

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    print "Ctrl+C captured, ending program."
    lcd_display(["clear"])
    GPIO.cleanup()
    sys.exit()

# check for motion by subscribing to the sensors/lightmotionvalue topic
def motion_checker():
    subscriber("sensors/lightmotionvalue")
    global prog_run
    global callb_msgpayload
    if callb_msgpayload.get("motionvalue", 0) == '1' and prog_run == False:
        prog_run = True
        ledControl('on', 'off')
        date_time = callb_msgpayload.get("datetimeid", "00-00-00_00:00:00")
        print "motion detected at " + date_time + "\n"
        add_motion_to_db(callb_msgpayload.get("lightvalue", 0), 1, date_time)
        rfid_checker()

def main():
    while True:
        lcd_display(["clear"])
        print "sensing for motion"
        ledControl('off', 'off')
        motion_checker()

if __name__ == '__main__':
    print "libaries import finished"

    signal.signal(signal.SIGINT, end_read)
    main()
