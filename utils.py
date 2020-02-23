# this python file is for shared functions amongst other python files
from gpiozero import Buzzer, LED  # for buzzer
import RPi.GPIO as GPIO # for operations requiring GPIO pins
import os
from picamera import PiCamera # for picam
from rpi_lcd import LCD # for lcd
import MFRC522 # for RFID reader
import time # for timing operations
from time import sleep
import serial # to read arduino
import json

# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import boto3
from boto3.dynamodb.conditions import Key, Attr

import string, random

def rand_str_gen(size=20):
    lettersal = ''.join(random.choice(string.ascii_letters) for i in range(size))
    lettersd = ''.join(random.choice(string.digits) for i in range(size))
    lettersp = ''.join(random.choice(string.punctuation) for i in range(size))
    letter = str(lettersal) + str(lettersd) + str(lettersp)
    return ''.join(random.choice(letter) for i in range(size))

# make the buzzer and led on and off to give the pulsating and blinking effect for 30 seconds
def buzzer():
    print "MAKE SOME NOISE!!!"
    bz = Buzzer(5) # buzzer at gpio 5
    redled = LED(19)
    t_end = time.time() + 30
    while time.time() < t_end:
        try:
            print "on buzzer and led"
            bz.on()
            redled.on()
            sleep(0.25)
            print "off buzzer and led"
            bz.off()
            redled.off()
            sleep(0.25)
        except Exception:
            bz.off()
            redled.off()

def camera(date_time):
    print "getting picture\n"
    # cam_stream = BytesIO(b"")
    camera = PiCamera()
    # camera.start_preview()
    sleep(2)
    # camera.capture(cam_stream, 'jpeg')
    dir_path = "/home/pi/motion_captures/"
    image_name = date_time + ".jpeg"

    if os.path.isdir(dir_path) == True:
        camera.capture(dir_path + image_name)
    else:
        try:
            os.mkdir(dir_path)
        except OSError:
            print ("Creation of the directory %s failed" % dir_path)
        else:
            print ("Successfully created the directory %s " % dir_path)

        camera.capture(dir_path + image_name)

    camera.close()
    print "stored image in " + dir_path + image_name
    return image_name

# function for all lcd display operations
# function takes in a list containing two strings
# and displays them in two seperate rows
def lcd_display(text_list):

    lcd = LCD()
    print "displaying"
    print text_list
    try:
        if 'clear' in text_list[0]:
            lcd.clear()
        else:
            lcd.text(text_list[0], 1)
            lcd.text(text_list[1], 2)
        sleep(1)
    except Exception:
        lcd.clear()

# read rfid card
def rfid_reader():

    print "reading rfid card"
    uid = None

    # Create an object of the class MFRC522
    mfrc522 = MFRC522.MFRC522()

    # This loop keeps checking for chips over 60 seconds.
    t_end = time.time() + 60
    while time.time() <= t_end: #wait for 60 seconds for rfid card

        # Scan for cards
        (status,TagType) = mfrc522.MFRC522_Request(mfrc522.PICC_REQIDL)

        # If a card is found
        if status == mfrc522.MI_OK:
            # Get the UID of the card
            (status,uid) = mfrc522.MFRC522_Anticoll()
            # if uid!=prev_uid:
            #    prev_uid = uid
            print("UID of card is {}".format(uid))
            return str(uid)
    return "timeout" # if no card return string timeout

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


# https://stackoverflow.com/a/55734992
# converts unicode dict to utf-8
def utfy_dict(dic):
    if isinstance(dic,unicode):
        return(dic.encode("utf-8"))
    elif isinstance(dic,dict):
        for key in dic:
            dic[key] = utfy_dict(dic[key])
        return(dic)
    elif isinstance(dic,list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict(e))
        return(new_l)
    else:
        return(dic)

class DynamoDB_class():
    def __init__(self):
    	self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    # def get_item(self, condition, tb_name, part_name, col_name, search_str, limit=0):
    def get_item(self, tb_name, keycondexpress, limit=0):
        try:
            print("get_item function")
            print(tb_name)
            print(limit)

            table = self.dynamodb.Table(tb_name)
    		# deviceid = "deviceid_dorachua"

    		# keycondexpress = ""
    		# replace deviceid with your partition key name
    		# if condition == "equals":
    		# 	# keycondexpress=Key('deviceid').eq(deviceid) & Key(col_name).eq(search_str)
    		#
    		# elif condition == "begins_with":
    		# 	# keycondexpress=Key('deviceid').eq(deviceid) & Key(col_name).begins_with(search_str)
    		#
    		# elif condition == "between":
    		# 	# keycondexpress=Key('deviceid').eq(deviceid) & Key(col_name).between(search_str)

    		# Query requires a partition key (aka (usually) your first column in the table) (for smol amts of data)
    		# BatchGetItems requires a primary key (aka your partition key + sort key or just partition key if dh sort key) (for large amts of data)
    		# Further reading: https://stackoverflow.com/questions/30749560/whats-the-difference-between-batchgetitem-and-query-in-dynamodb/30772172
            response = table.query(
            	KeyConditionExpression=keycondexpress,
            	ScanIndexForward=False
            )
            items = response['Items']
            if limit == 0:
                    data = items
            else:
                    data = items[:n] # limit to last n-th items
            data_reversed = data[::-1]
            data_reversed_c = []
            for i in data_reversed:
                data_reversed_c.append(utfy_dict(i))
            print("getitemresult_utils")
            print(data_reversed_c)
            print("end of getitemresult_utils")
            return data_reversed_c
        except:
            import sys
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

    def add_item(self, tb_name, item):
    	table = dynamodb.Table(tb_name)

    	response = table.put_item(
    	   Item=item
    	)

    	print("PutItem succeeded:")
    	print(json.dumps(response, indent=4, cls=DecimalEncoder))

    # Usage:
    # key = {
    # 	"deviceid": "deviceid_dorachua",
    # 	"datetimeid": "2020-01-22T18:53:30.459146"
    # }
    # update_express = 'set item_value = :v'
    # express_attr_values = {
    # 	':v': 100
    # }
    # if express_attr_names=="":
	# def update_item(self, tb_name, key, update_express, express_attr_values, express_attr_names):
    def update_item(self, tb_name, key, update_express, express_attr_values):
        self.table = self.dynamodb.Table(tb_name)
        response = self.table.update_item(
            Key=key,
            UpdateExpression=update_express,
            ExpressionAttributeValues=express_attr_values
        )

        # Usage:
        # key = {
        # 	"deviceid": "deviceid_dorachua",
        # 	"datetimeid": "2020-01-22T18:53:30.459146"
        # }
        # update_express = 'set #v = :v'
        # express_attr_values = {
        # 	':v': 100
        # }
        # express_attr_names = {
        # 	'#v': "value"
        # }
        # else:
        #     response = table.update_item(
        #         Key=key,
        #         UpdateExpression=update_express,
        #         ExpressionAttributeValues=express_attr_values,
        #         ExpressionAttributeNames=express_attr_names
        #     )

        print("UpdateItem succeeded:")
        print(json.dumps(response, indent=4, cls=DecimalEncoder))

    def delete_item(self, tb_name, del_key):
            print("Attempting a conditional delete...")
            try:
                    table = self.dynamodb.Table(tb_name)

                    # Usage
                    # key = {
                    # 	"deviceid": "deviceid_dorachua",
                    # 	"datetimeid": "2020-01-22T18:53:31.756004"
                    # }

                    response = table.delete_item(
                    Key=del_key
                    # ConditionExpression="info.rating <= :val", # do not delete item if doesn't meet condition
                    # ExpressionAttributeValues= {
                    #     col_name: del_key
                    # }
                )
            except ClientError as e:
                if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                    print(e.response['Error']['Message'])
                else:
                    raise Exception
            else:
                print("DeleteItem succeeded:")
                print(json.dumps(response, indent=4, cls=DecimalEncoder))
