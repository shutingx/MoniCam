# MoniCam
A monitoring security and access control system

## Introduction
This application is a home security monitoring system, which consists of a Pi Camera that is motion activated using a motion sensor, and also a RFID reader to ‘allow access’ through the use of RFID cards. When an authenticated RFID is used, facial recognition will confirm that the current user is the card owner. On the other hand, when there is 3 unsuccessful attempts to ‘get access’ by using unknown RFID id cards, it will alert the user through telegram alert with a picture and sound the alarm for 30 seconds. Moreover, when the light intensity falls below a certain level, the LED will light up to assist doing facial recognition and taking pictures. 

The user can use the web interface to sound alarm, see the status of the motion sensor, real time and historical data of motion sensed and attempts, and add/modify/delete users. 

The owner can send various commands to the telegram bot such as getting it to take pictures, ring alarms, chat with guests who use the bot too and displaying text on the lcd display.

## Setup instructions
Please refer to the monicam_documentation.pdf for instructions on how to set this project up.

## Using it
Follow the steps here:
1)	First connect hardware as in Section 2 and the Fritzing diagram.
2)	Go through all the instructions in Section 3.
3)	Then run the server.py file for web server.
4)	Run the telegrambot.py for Telegram bot.
5)	Run the monicam_main.py for the main program.
6)	Run the lightmotion.py
7)	Run the alarmdetector.py
8)	Access the webpage by typing <your AWS public IPv4 address>:5000

## Hardware checklist
You need the following hardware in order to do this project:
1.	1 LDR (light sensor)
2.	1 PIR motion sensor
3.	1 RFID Card reader +  3 RFID cards
4.	I2C 16x2 LCD display
5.	3 LEDs (1 red, yellow and green LED)
6.	2 Piranha LEDs
7.	1 Buzzer
8.	Raspberry Pi camera (piCam)
9.	4 330Ω resistors (for 3 LEDs and 2 piranha LEDS)
10.	1 10kΩ resistor (for light sensor)
11.	Arduino
12.	Raspberry Pi
13.	USB cable (for connecting Arduino and Raspberry Pi)
14.	T-Cobbler breadboard
15.	Half breadboard

## Python libraries used
This is the list of libraries required for this project:
1.	boto3 library
2.	botocore library
3.	json library
4.	telepot library
5.	MFRC522 library
6.	rpi_lcd library
7.	AWSIoTPythonSDK library
8.	paho-mqtt library

