from __future__ import unicode_literals
import itchat, logging, time, sys, json
from itchat.content import *
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("wechat_transfer_bot")
logger.setLevel(logging.INFO)
logger.addHandler(TimedRotatingFileHandler('bot.log', when="midnight", interval=1, backupCount=30))
logger.addHandler(logging.StreamHandler(sys.stdout))

# login
itchat.auto_login(enableCmdQR=2, hotReload=True)

# read chatroom nicknames
transfer_rooms_nickname = []
with open("chatrooms.txt", "r") as fp:
    for line in fp:
        room = line.strip()
        transfer_rooms_nickname.append(room)
        logger.info("added chatroom %s for transfer" % room)

# get group usernames based on nicknames
all_chatrooms_raw = itchat.get_chatrooms()

# a mapping for all chatrooms from username to nickname
rooms_username_to_nickname = {room.get('UserName'): room.get("NickName") for room in all_chatrooms_raw}

# username of rooms for transfering message
transfer_rooms_username = [room.get('UserName') for room in all_chatrooms_raw if
                           room.get('NickName') in transfer_rooms_nickname]
logger.info("rooms to transfer: %s" %
            json.dumps({username: rooms_username_to_nickname[username] for username in transfer_rooms_username},
                       sort_keys=True, indent=4, ensure_ascii=False))


@itchat.msg_register([TEXT, MAP, CARD, NOTE, SHARING, PICTURE, RECORDING, ATTACHMENT, VIDEO], isGroupChat=True)
def group_reply_text(msg):
    global rooms_username_to_nickname
    msg_type = msg['Type']
    logger.debug("received %s msg: %s" % (msg_type, msg))

    from_room_username = msg['FromUserName']

    if not from_room_username.startswith("@@"):
        logger.info("ignored non chatroom msg from %s" % from_room_username)
        return

    if from_room_username not in transfer_rooms_username:
        logger.info("ignored msg from %s" % rooms_username_to_nickname[from_room_username])
        return

    from_room_nickname = rooms_username_to_nickname[from_room_username]
    from_actual_nickname = msg['ActualNickName']
    logger.info(
        "received %s msg from %s in chatroom %s" % (msg_type, from_actual_nickname, from_room_nickname))

    for dest_room_username in transfer_rooms_username:
        if (from_room_username == dest_room_username):
            continue

        if msg_type == TEXT or msg_type == NOTE:
            content = msg["Content"]
            r = itchat.send_msg("%s (from %s):\n%s" % (from_actual_nickname, from_room_nickname, content),
                                toUserName=dest_room_username)
            logger.info("resp = %s" % r)
        elif msg_type == SHARING or msg_type == MAP:
            content = "shared %s: %s" % (msg["FileName"], msg["Url"])
            r = itchat.send_msg("%s (from %s):\n%s" % (from_actual_nickname, from_room_nickname, content),
                                toUserName=dest_room_username)
            logger.info("resp = %s" % r)
        elif msg_type == CARD:
            content = "shared a contact: %s" % msg['Text']["NickName"]
            r = itchat.send_msg("%s (from %s):\n%s" % (from_actual_nickname, from_room_nickname, content),
                                toUserName=dest_room_username)
            logger.info("resp = %s" % r)

        elif msg_type == PICTURE or \
                msg_type == RECORDING or \
                msg_type == ATTACHMENT or \
                msg_type == VIDEO:

            filename = msg['FileName']
            msg.download("download/%s" % filename)

            itchat.send_msg("%s (from %s):\nsent a %s" % (from_actual_nickname, from_room_nickname, msg_type),
                            toUserName=dest_room_username)
            r = itchat.send('@%s@%s' %
                            ('img' if msg['Type'] == 'Picture' else 'fil', "download/%s" % filename),
                            dest_room_username)
            logger.info("resp = %s" % r)

        logger.info("%s msg from %s transferred to room %s" % (
            msg_type, from_actual_nickname, rooms_username_to_nickname[dest_room_username]))

itchat.run()
