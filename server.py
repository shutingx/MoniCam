from flask import Flask, render_template, jsonify, request,Response,redirect, send_from_directory
import sys

import json
import numpy

import decimal

import gevent
import gevent.monkey

from gevent.pywsgi import WSGIServer
from datetime import datetime
from time import sleep
# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import boto3
from boto3.dynamodb.conditions import Key, Attr
gevent.monkey.patch_all()

import string, random

deviceid = "monicam"
###############################################################################
# for mqtt and db functions

host = "" # <replace> with your AWS Endpoint
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"

callb_msgpayload = {}



# random string generator
def rand_str_gen(size=10):
    lettersal = ''.join(random.choice(string.ascii_letters) for i in range(size))
    lettersd = ''.join(random.choice(string.digits) for i in range(size))
    lettersp = ''.join(random.choice(string.punctuation) for i in range(size))
    letter = str(lettersal) + str(lettersd) + str(lettersp)
    return ''.join(random.choice(letter) for i in range(size))

# Custom MQTT message callback
def customCallback(client, userdata, message):
    global callb_msgpayload
    callb_msgpayload = json.loads(message.payload)

# ---------------------------------------------------------#

def publisher(topic, message):
    server_mqtt = AWSIoTMQTTClient("monicamMQTT_pub" + rand_str_gen())
    server_mqtt.configureEndpoint(host, 8883)
    server_mqtt.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    server_mqtt.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    server_mqtt.configureDrainingFrequency(2)  # Draining: 2 Hz
    server_mqtt.configureConnectDisconnectTimeout(10)  # 10 sec
    server_mqtt.configureMQTTOperationTimeout(5)  # 5 sec
    server_mqtt.connect()
    server_mqtt.publish(topic , json.dumps(message), 1)
    sleep(2)
    server_mqtt.disconnect()

def subscriber(topic):
    server_mqtt = AWSIoTMQTTClient("monicamMQTT_sub" + rand_str_gen())
    server_mqtt.configureEndpoint(host, 8883)
    server_mqtt.configureCredentials(rootCAPath, privateKeyPath, certificatePath)
    server_mqtt.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    server_mqtt.configureDrainingFrequency(2)  # Draining: 2 Hz
    server_mqtt.configureConnectDisconnectTimeout(10)  # 10 sec
    server_mqtt.configureMQTTOperationTimeout(5)  # 5 sec
    server_mqtt.connect()
    server_mqtt.subscribe(topic, 1, customCallback)
    sleep(2)
    server_mqtt.unsubscribe(topic)
    server_mqtt.disconnect()

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

class GenericEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, numpy.generic):
            return numpy.asscalar(obj)
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)

def data_to_json(data):
    json_data = json.dumps(data,cls=GenericEncoder)
    print(json_data)
    return json_data

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
                    data = items[:limit] # limit to specified amt of items
            data_reversed = data[::-1]
            data_reversed_c = []
            for i in data_reversed:
                data_reversed_c.append(utfy_dict(i))
            return data_reversed_c
        except:
            import sys
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

    def add_item(self, tb_name, item):
    	table = self.dynamodb.Table(tb_name)

    	response = table.put_item(
    	   Item=item
    	)

    	print("PutItem succeeded:")
    	print(json.dumps(response, indent=4, cls=DecimalEncoder))

    def updating_item(self, tb_name, key, update_express, express_attr_values):
    	table = self.dynamodb.Table(tb_name)
        # Usage:
        # key = {
        # 	"deviceid": "deviceid_dorachua",
        # 	"datetimeid": "2020-01-22T18:53:30.459146"
        # }
        # update_express = 'set item_value = :v'
        # express_attr_values = {
        # 	':v': 100
        # }
        # if express_attr_names == '':
        response = table.update_item(
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

	def deleting_item(self, tb_name, del_key):
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

################################################################################
db = DynamoDB_class()

def get_userid():
    print("getting userid")
    user_info_list = []
    dict = {}
    user_list = []
    try:
        keycondexpress = Key("deviceid").eq(deviceid)
        user_info_list = db.get_item("user_info", keycondexpress)
        # print(user_info_list)
        # for i in user_info: # converting to utf-8 dict from unicode
        #     user_info_list.append(utfy_dict(i))
        for user in user_info_list:
            user_list.append(user["id"])
        # print(user_info_list)
        # print(user_list)
        return user_list
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


app = Flask(__name__)

###############################################################################
# for getting historical data

# for serving the graph page
@app.route("/charts.html")
def charts():
    print("getting chart webpage")
    return render_template("charts.html")

# for the all time motion graph data
@app.route("/api/get_alltime_motion_graph_data",methods = ['POST', 'GET'])
def apidata_getalltimemotiongraphdata():
    print("getting all time motion data")
    if request.method == 'GET':
        try:
            keycondexpress=Key('deviceid').eq(deviceid)
            dbdata = db.get_item("lightmotion_tb", keycondexpress)
            prev_motion_date = ''
            cur_motion_date = ''
            motion_count = 0
            dict = {}
            motion_array = []
            for i in dbdata:
                cur_motion_date = (i.get('motion_datetime', None))[0:10]
                if prev_motion_date == '':
                    prev_motion_date = cur_motion_date
                    motion_count = 1
                elif prev_motion_date == cur_motion_date:
                    motion_count += 1
                else:
                    dict = {
                        'date': prev_motion_date,
                        'motion': motion_count
                    }
                    motion_array.append(dict)
                    prev_motion_date = cur_motion_date
                    motion_count = 1
            dict = {
                'date': prev_motion_date,
                'motion': motion_count
            }
            motion_array.append(dict)
            data = {'chart_data': data_to_json(motion_array), 'title': "Historical LightMotion Graph Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

# for the all time motion table data
@app.route("/api/get_alltime_motion_table_data",methods = ['POST', 'GET'])
def apidata_getalltimemotiontabledata():
    print("getting all time motion data")
    if request.method == 'GET':
        try:
            keycondexpress=Key('deviceid').eq(deviceid)
            dbdata = data_to_json(db.get_item("lightmotion_tb", keycondexpress))
            data = {'chart_data': dbdata, 'title': "Historical LightMotion Table Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

# for the all time attempt graph
@app.route("/api/get_alltime_attempt_graph_data",methods = ['POST', 'GET'])
def apidata_getattemptgraphdata():
    print("getting all time attempt data")
    if request.method == 'GET':
        try:
            keycondexpress=Key('deviceid').eq(deviceid)
            dbdata = db.get_item("attempt_tb", keycondexpress)
            prev_attempt_date = ''
            cur_attempt_date = ''
            attempt_count = 0
            dict = {}
            attempt_array = []
            for i in dbdata:
                cur_attempt_date = (i.get('attempt_datetime', None))[0:10]
                if prev_attempt_date == '':
                    prev_attempt_date = cur_attempt_date
                    attempt_count = 1
                elif prev_attempt_date == cur_attempt_date:
                    attempt_count += 1
                else:
                    dict = {
                        'date': prev_attempt_date,
                        'attempt': attempt_count
                    }
                    attempt_array.append(dict)
                    prev_attempt_date = cur_attempt_date
                    attempt_count = 1
            dict = {
                'date': prev_attempt_date,
                'attempt': attempt_count
            }
            attempt_array.append(dict)
            data = {'chart_data': data_to_json(attempt_array), 'title': "Historical Attempt Graph Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

# for the all time attempt table
@app.route("/api/get_alltime_attempt_table_data",methods = ['POST', 'GET'])
def apidata_getattempttabledata():
    print("getting all time attempt data")
    if request.method == 'GET':
        try:
            keycondexpress=Key('deviceid').eq(deviceid)
            dbdata = data_to_json(db.get_item("attempt_tb", keycondexpress))
            data = {'chart_data': dbdata, 'title': "Historical Attempt Table Data"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

###############################################################################
# for rfid forms

@app.route("/forms.html",methods = ['POST', 'GET'])
def username():
    userid = get_userid()
    return render_template("forms.html", userid=userid)

@app.route("/api/get_user_data", methods = ['POST', 'GET'])
def get_user():
    print("getting user data for table")
    if request.method == 'POST':
        try:
            keycondexpress=Key('deviceid').eq(deviceid)
            dbdata = data_to_json(db.get_item("user_info", keycondexpress))
            data = {'chart_data': dbdata, 'title': "User Info Table"}
            return jsonify(data)
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

@app.route("/form_add_user", methods = ['POST', 'GET'])
def add_user():
    print("recieving data from add user form")
    add_feedback = "adding user data was not successful!"
    if request.method == "POST":
        print(request.form)
        missing = list()

        for k, v in request.form.items():
            if v == "":
                missing.append(k)

        if missing:
            missing_str = ""
            for i in missing:
                missing_str = missing_str + ", " + i
            feedback = "Missing field(s) for {}".format(missing_str)
        else:
            Rfid_ID = request.form.get("add_Rfid_ID")
            username = request.form.get("add_username")
            userid = get_userid()
            print(userid)
            if userid == []:
                userid = 'u1'
            else:
                userid = 'u' + str(len(userid) + 1)
            date_time = str(datetime.now().replace(microsecond=0))
            item = {}
            item["deviceid"] = deviceid
            item["id"] = userid
            item["rfid_id"] = Rfid_ID
            item["username"] = username
            item["modification_date"] = date_time
            db.add_item("user_info", item)
            add_feedback = "Successfully added user entry!"
    userid = get_userid()
    return render_template("forms.html", add_feedback=add_feedback, userid=userid)

@app.route("/form_modify_user", methods = ['POST', 'GET'])
def modify_user():
    print("recieving data from modify user form")
    modify_feedback = "modifying user data was not successful!"
    if request.method == "POST":
        id = request.form.get("mod_id")
        Rfid_ID = request.form.get("mod_Rfid_ID")
        username = request.form.get("chg_username")
        date_time = str(datetime.now().replace(microsecond=0))

        missing = list()

        for k, v in request.form.items():
            if v == "":
                missing.append(k)

        if missing:
            missing_str = ""
            for i in missing:
                missing_str = missing_str + ", " + i
            feedback = "Missing field(s) for {}".format(missing_str)
        else:
            key={
            	"deviceid": deviceid,
            	"id": id,
            }
            update_express='set rfid_id = :rid, username = :uname, modification_date = :mod_date'
            express_attr_values={
            	':rid': Rfid_ID,
            	':uname': username,
                ':mod_date': date_time
            }
            db.updating_item("user_info", key, update_express, express_attr_values)
            modify_feedback = "Successfully edited user entry!"
    userid = get_userid()
    return render_template("forms.html", modify_feedback=modify_feedback, userid=userid)

@app.route("/form_delete_user", methods = ['POST', 'GET'])
def delete_user():
    print("recieving data from delete user form")
    delete_feedback = "deleting user data was not successful!"
    if request.method == "POST":
        id = request.form.get("del_id")

        missing = list()

        for k, v in request.form.items():
            if v == "":
                missing.append(k)

        if missing:
            missing_str = ""
            for i in missing:
                missing_str = missing_str + ", " + i
            delete_feedback = "Missing field(s) for {}".format(missing_str)
        else:
            key = {
            	'deviceid': deviceid,
                'id': id
            }
            print("Attempting a conditional delete...")
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            try:
            	table = dynamodb.Table("user_info")

            	# Usage
            	# key = {
            	# 	"deviceid": "deviceid_dorachua",
            	# 	"datetimeid": "2020-01-22T18:53:31.756004"
            	# }

            	response = table.delete_item(
                    Key=key
                )
            except ClientError as e:
                if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                    print(e.response['Error']['Message'])
                else:
                    raise Exception
            else:
                print("DeleteItem succeeded:")
                print(json.dumps(response, indent=4, cls=DecimalEncoder))
            delete_feedback = "Successfully deleted user entry!"
    userid = get_userid()
    return render_template("forms.html", delete_feedback=delete_feedback, userid=userid)

################################################################################
# for index page content

# for displaying the index page
@app.route("/")
@app.route("/index.html")
def index():
    print("getting the index page")
    return render_template('index.html')

#####################################################
# Get time configuration

# to show the most recent setting of start time range for the day
@app.route('/api/startTimeRange', methods=['POST', 'GET'])
def getStartTimeRange():
    timerange = []
    if request.method == 'GET':
        try:
            keycondexpress=Key("deviceid").eq(deviceid) & Key("timeconf_datetime").begins_with(datetime.today().strftime('%Y-%m-%d'))
            startrange = db.get_item("timeconfig", keycondexpress, limit=1)
            if startrange == []:
                return jsonify("None")
            else:
                return jsonify(startrange[0]["starttime"])
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

# to show the most recent setting of end time range for the day
@app.route('/api/endTimeRange', methods=['POST', 'GET'])
def getEndTimeRange():
    timerange = []
    if request.method == 'GET':
        try:
            keycondexpress=Key("deviceid").eq(deviceid) & Key("timeconf_datetime").begins_with(datetime.today().strftime('%Y-%m-%d'))
            endrange = db.get_item("timeconfig", keycondexpress, limit=1)
            if endrange == []:
                return jsonify("None")
            else:
                return jsonify(endrange[0]["endtime"])
        except:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

# to get user input from HTML and store into DB
@app.route('/api/getTimeConfig', methods=['POST', 'GET'])
def getTimeConfig():
    if request.method == 'POST':
        starttime = str(request.form.get('starttime'))
        endtime = str(request.form.get('endtime'))
        timeconf_datetime = str(datetime.now().replace(microsecond=0)).replace(" ", "_")
        item={
            "deviceid": deviceid,
            "timeconf_datetime": timeconf_datetime,
            "starttime": starttime,
            "endtime": endtime
        }
        db.add_item("timeconfig", item)
        return redirect('/')
    else:
        abort(405)


##########################################
# For mqtt calls for alarm and live data

# for ringing the alarm
@app.route("/api/alert/alarm", methods=['POST'])
def apialarm():
    try:
        print("ringing the alarm")
        message={}
        message["alarm"] = 1
        publisher("api/alert/alarm", message)
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


# for getting the motion status
@app.route("/api/motionstatus", methods=['GET'])
def apimotionstatus():
    try:
        print("checking motion status")
        subscriber("sensors/lightmotionvalue")
        global callb_msgpayload
        motion = callb_msgpayload.get("motionvalue", "nth")
        print(motion)
        status_str = ''
        if motion == '1':
            status_str = "Motion detected!"
        else:
            status_str = "No motion detected."
        return jsonify({'status': status_str})
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])


# for getting the light intensity
@app.route("/api/lightvalue", methods=['GET'])
def apilightstatus():
    try:
        print("checking light intensity")
        subscriber("sensors/lightmotionvalue")
        global callb_msgpayload
        light_value = callb_msgpayload.get("lightvalue", "nth")
        status_str = ''
        if light_value == "nth":
            status_str = "No light value"
        else:
            status_str = light_value
        return jsonify({'status': status_str})
    except:
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])

################################################################################
# main
def main():
    try:
         http_server = WSGIServer(('0.0.0.0', 5000), app)
         app.debug = True
         http_server.serve_forever()
         print('Server waiting for requests')
    except KeyboardInterrupt:
        sys.exit()
    except:
         print("Exception")
         print(sys.exc_info())

if __name__ == '__main__':
   main()
