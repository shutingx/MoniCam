from picamera import PiCamera
from utils import camera
import boto3
import time
import os
from datetime import datetime
import sys
from time import sleep

if len(sys.argv) == 1:
	print("Please supply username.\n" +
	"Username has to be the same as the username in user_info.")
	sys.exit()
elif len(sys.argv) == 2:
	if sys.argv[1] == '-h' or sys.argv[1] == '--help':
		print("Supply a username that is the same as the username in user_info.")
		sys.exit()
else:
	print("Too many arguments! Supply only the username!")
	sys.exit()



# #initialize reckognition sdk
# client = boto3.client('rekognition', region_name='us-east-1')
# with open("/home/pi/motion_captures/" + filepath, mode='rb') as file:
# 	response = client.index_faces(Image={'Bytes': file.read()}, CollectionId="monicamrekognition", ExternalImageId=filepath, DetectionAttributes=['ALL'])
# print response

# To store images to s3
def s3_imgstore():
	print("Taking image in 3 seconds!")
	for i in range(3, 0, -1):
		print(i)
		sleep(1)
	filepath = camera(str(sys.argv[1]))
	print("Picture taken.")
	# Create an S3 resource
	s3 = boto3.resource('s3', region_name='us-east-1')

	# Set the bucket name
	img_bucket = 'monicamrekognition' # <replace> with your own unique bucket name
	dir_path = "/home/pi/motion_captures/" # <replace> with your own image directory
	exists = True

	try:
	    s3.meta.client.head_bucket(Bucket=img_bucket)
	except botocore.exceptions.ClientError as e:
	    error_code = int(e.response['Error']['Code'])
	    if error_code == 404:
	        exists = False

	if exists == False:
	  s3.create_bucket(Bucket=img_bucket,CreateBucketConfiguration={
	    'LocationConstraint': 'us-east-1'})

	# Upload a new file
	s3.Object(img_bucket, filepath).put(Body=open(dir_path + filepath, 'rb'))
	print("File uploaded")

if __name__ == '__main__':
	s3_imgstore()
