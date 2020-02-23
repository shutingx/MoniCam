import telepot
from gpiozero import LED
from time import sleep
from datetime import datetime
import RPi.GPIO as GPIO # for operations requiring GPIO pins
import glob
from utils import camera, buzzer, lcd_display
import wget

my_bot_token = '' # <replace> with your bot token
bot = telepot.Bot(my_bot_token)
display = False
proxy_chat = False
proxy_chat_status = 'Inactive'
guest_chat_id = 0
owner_chat_id = # <replace> with your own chat id

def dateTimefunc():
    date_time = str(datetime.now()).replace(" ", "_")
    return date_time

def send_user_Msg(command, data=None):
    import telepot
    global owner_chat_id
    bot = telepot.Bot(my_bot_token)

    if command == 'failed_attempts':
        bot.sendMessage(owner_chat_id, '3 failed attempts have been detected!')
        bot.sendPhoto(owner_chat_id, photo=open("/home/pi/motion_captures/" + camera(dateTimefunc()), 'rb'))
        print('Latest picture has been sent.')
    elif command == 'success':
        bot.sendMessage(owner_chat_id, data + ' is at home.')
    elif command == 'uauth_user':
        bot.sendMessage(owner_chat_id, 'Unauthorised user of ' + data + '\'s RFID card!')
        bot.sendPhoto(owner_chat_id, photo=open("/home/pi/motion_captures/" + camera(dateTimefunc()), 'rb'))

def respondToMsg(msg):
    print(msg)
    file_id = ''
    chat_id = msg['chat']['id']
    command = (msg.get('text', 'msg_is_img')).lower()
    if command == 'msg_is_img':
        file_id = msg['photo'][0]['file_id']
    global display
    global guest_chat_id
    global proxy_chat
    global proxy_chat_status
    global owner_chat_id

    print('Got chat_id: {}'.format(chat_id))
    print('Got command: {}'.format(command))

    if 'Active' in proxy_chat_status:
        if chat_id == guest_chat_id:
            if 'exit()' in command:
                bot.sendMessage(owner_chat_id, 'Guest has left the chat.')
                bot.sendMessage(guest_chat_id, 'You have left the chat.')
                proxy_chat = False
                proxy_chat_status = 'Inactive'
                guest_chat_id = 0
            else:
                bot.sendMessage(owner_chat_id, command)
        elif chat_id == owner_chat_id:
            if 'exit()' in command:
                bot.sendMessage(guest_chat_id, 'Owner has left the chat.')
                bot.sendMessage(owner_chat_id, 'You have left the chat.')
                proxy_chat = False
                proxy_chat_status = 'Inactive'
                guest_chat_id = 0
            elif 'guestid' in command:
                bot.sendMessage(owner_chat_id, 'Current guest chat id is {}'.format(guest_chat_id))
            else:
                bot.sendMessage(guest_chat_id, command)
    elif proxy_chat == True and 'Inactive' in proxy_chat_status:
        if 'yes' in command.lower():
            bot.sendMessage(owner_chat_id, 'Connecting you to guest now...\n'+
            'To end convo with guest, please type \'exit()\'.\n'+
            'Type guestid to get the chat id of the current guest.')
            bot.sendMessage(guest_chat_id, 'Owner has accepted your chat request.\n'+
            'To end convo with owner, please type \'exit()\'.')
            proxy_chat_status = 'Active'
        elif 'no' in command.lower():
            bot.sendMessage(owner_chat_id, 'Communication request by guest declined.')
            bot.sendMessage(guest_chat_id, 'Communication request declined by owner.')
            guest_chat_id = 0
            proxy_chat = False
    # display help message to users
    elif command == '/help':
        bot.sendMessage(chat_id, 'Hello!\nI am a surveillance camera bot')
        if chat_id == owner_chat_id:
            bot.sendMessage(owner_chat_id, 'Here is a list of available commands you can ask me to do:\n'+
            '/help - displays this help message.\n'+
            'pic / picture / image - takes a real time picture.\n'+
            'display / lcd - displays a message on the lcd screen.\n'+
            'alarm - sounds the alarm.\n'+
            'chat_id - gets your chat id with the bot.')
        else:
            bot.sendMessage(chat_id, 'Here is a list of available commands you can ask me to do:\n'+
            'chat_id - gets your chat id with the bot.\n'+
            'talk / owner / msg / message - talk to the owner.')
    # for all the owner allowed commands
    elif chat_id == owner_chat_id:
        if 'pic' in command or 'picture' in command or 'image' in command:
            print('Taking an image')
            bot.sendPhoto(owner_chat_id, photo=open("/home/pi/motion_captures/" + camera(dateTimefunc()), 'rb'))
            bot.sendMessage(owner_chat_id, 'This is the real time ' + command)
        # for owner to display text on lcd with text split into 2 lines using newline
        # as a delimiter
        elif display == True:
            txt = command.split("\n")
            if len(txt) == 1:
                txt.append('')
            if 'exit()' in txt[0]:
                display = False
                bot.sendMessage(owner_chat_id, 'Exited lcd display mode.')
            else:
                lcd_display(txt)
        # for owner to display text on lcd display
        elif 'display' in command or 'lcd' in command:
            bot.sendMessage(owner_chat_id,
            'Please enter what you want to say to the visitor.\n' +
            'Only 16 characters per line; Maximum of 2 lines.\n' +
            'Press the enter key to split your strings into two lines\n' +
            'Eg.\n Hello\nWorld\n'+
            'Type exit() to exit sending text to lcd display.')
            display = True
        # for owner to sound the alarm
        elif 'alarm' in command:
            bot.sendMessage(owner_chat_id, 'Sounding the alarm now!\n'+
            'Please wait for alarm to stop ringing before inputting any more commands.')
            buzzer()
            bot.sendMessage(owner_chat_id, 'Alarm has finished ringing.')
        elif ('talk' in command or "owner" in command or 'msg' in command or 'message' in command):
            bot.sendMessage(owner_chat_id, 'Displaying proxy chat instructions to guest')
            for x in range(2):
                lcd_display(['Hello guest!', 'Please use the'])
                sleep(2)
                lcd_display(['Telegram bot', 'monicam_bot'])
                sleep(2)
                lcd_display(['to communicate', 'with the owner'])
                sleep(2)
                lcd_display(['Start the bot', 'and type chat'])
                sleep(2)
                lcd_display(['to chat with', 'the owner'])
                sleep(2)
                lcd_display(['clear'])
        elif 'chat_id' in command:
            bot.sendMessage(chat_id, 'Your chat id is {}'.format(chat_id))
        # for all the other commands not here
        else:
            bot.sendMessage(chat_id, 'Unknown command. Please try again.\n' +
            'For a list of available commands, type /help.')
    # for getting the chat id of the current user
    elif 'chat_id' in command:
        bot.sendMessage(chat_id, 'Your chat id is {}'.format(chat_id))
    # for guest to communicate with the owner
    elif ('talk' in command or "owner" in command or 'msg' in command or 'message' in command) and chat_id != owner_chat_id:
        # if chat_id == owner_chat_id:
        #     bot.sendMessage(owner_chat_id, 'Enter the chat id of the guest.')
        guest_chat_id = chat_id
        bot.sendMessage(owner_chat_id, 'guest with chat_id ' + str(guest_chat_id) +
        ' wants to talk to you. Do you accept or not? (Yes or No)')
        proxy_chat = True
    # for all the other commands not here
    else:
        bot.sendMessage(chat_id, 'Unknown command. Please try again.\n' +
        'For a list of available commands, type /help.')


def main():
    bot.message_loop(respondToMsg)
    # bot.sendMessage(chat_id, 'nanana')
    print('Listening for RPi commands...')

    while True:
        sleep(10)

if __name__ == '__main__':
    main()
