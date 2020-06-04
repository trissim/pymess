#!/usr/bin/python
import fbchat
import asyncio
import jsonpickle
import websockets
import argparse
import pickle
import json
from notify import notification
from collections import OrderedDict
from collections import namedtuple
from subprocess import call

all_users = {}
all_messages = {}
conversations = OrderedDict()
s = None
host = None
port = None
client = None
commands = []
websocket = None


class conversation(object):
    def __init__(self, thread):
        self.thread = thread
        self.group = (thread.type == fbchat.ThreadType.GROUP)
        self.users = self.get_users()
        self.messages = []
        self.buffer = []

    def update(self):
        self.name = self.convo_name()

    def convo_name(self):
        if self.group:
            return self.get_groupname()
        else:
            return self.get_username()

    def get_username(self, uid=None):
        if self.group:
            try:
                return self.thread.nicknames[str(uid)]
            except:
                return all_users[str(uid)].name
        else:
            if self.thread.nickname is None:
                return self.thread.name
            else:
                return self.thread.nickname

    def get_groupname(self):
        if self.thread.name == None:
            return self.create_groupname()
        else:
            return self.thread.name

    def get_users(self):
        if self.group:
            return list(self.thread.participants)
        else:
            return [self.thread.uid]

    def buffer_message(self, msg_uid):
        msg = all_messages[str(msg_uid)]
        if not msg.author in self.users:
            username = "Me"
        else:
            username = self.get_username(uid=msg.author)
        self.buffer.append(username+":\n"+str(msg.text))

    def create_groupname(self, style='short'):
        names = []
        users = [all_users[participant]
                 for participant in self.thread.participants]
        if style == "short":
            names = [user.first_name for user in users]
        name = ", ".join(names[:2])
        if len(names) > 2:
            name = name + " + "+str(len(names[-1]))
        return name

    def get_dict(self):
        convo_dict = {"thread": self.thread,
                      "group": self.group,
                      "name": self.convo_name(),
                      "usernames": {uid: self.get_username(uid) for uid in self.get_users()},
                      "users": self.get_users(),
                      "messages": self.messages,
                      "buffer": self.buffer}
        return convo_dict


loop = asyncio.get_event_loop()


async def get_user_infos(client, users):
    if type(users) is not str:
        users = set(users)
    else:
        users = set([users])

    users = list(users - (set(all_users.keys())))

    users = await client.fetch_user_info(*users)
    for uid, user in users.items():
        all_users[uid] = user


async def init_users(client):
    global conversations
    users = await client.fetch_all_users()
    for user in users:
        all_users[str(user.uid)] = user
    convo_users = []
    for conversation in conversations.values():
        convo_users += conversation.get_users()
    await get_user_infos(client, convo_users)


async def init_conversations(client, conversations, threads):
    conversations = {thread.uid: conversation(thread) for thread in threads}
    for convo in conversations.values():
        msgs = await client.fetch_thread_messages(convo.thread.uid)
        for msg in msgs:
            all_messages[str(msg.uid)] = msg
            convo.messages.append(msg.uid)
        convo.messages.reverse()
    return conversations


async def init_buffers(client, conversations):
    for convo in conversations.values():
        try:
            print("Convo name:", convo.convo_name())
        except KeyError as e:
            await get_user_infos(client, e.args[0])
            convo.update()
        for msg_uid in convo.messages:
            try:
                convo.buffer_message(msg_uid)
            except KeyError as e:
                await get_user_infos(client, e.args[0])
                convo.update()


class cli(fbchat.Client):
    async def on_message(self, author_id, message_object, thread_id, thread_type, **kwargs):
        await self.mark_as_delivered(thread_id, message_object.uid)
        global commands
        global all_messages
        all_messages[str(message_object.uid)] = message_object
        if not thread_id in conversations.keys():
            thread_info = await self.fetch_thread_info(thread_id)
            thread = list(thread_info.values())[0]
            new_convo = await init_conversations(self, {}, thread)
            conversations.update(new_convo)
        else:
            conversations[str(thread_id)].messages.append(
                message_object.uid)
        conversations[str(thread_id)].buffer_message(message_object.uid)
        asyncio.ensure_future(
            send("rcv_convo", [conversations[str(thread_id)].get_dict()]))
        call(["notify-send", all_users[str(author_id)].name + " says:",
              message_object.text, ])


loop = asyncio.get_event_loop()


async def init():
    global conversations

    cookies = {}
    try:
        with open('session.json', 'r') as f:
            cookies = json.load(f)
    except:
        pass
    await client.start("tristan6100@hotmail.com", "Roxy6100????", session_cookies=cookies)
    threads = await client.fetch_thread_list()
    conversations = await init_conversations(client, conversations, threads)
    await init_users(client)
    await init_buffers(client, conversations)


async def relay(ws, path):
    global commands
    global websocket
    websocket = ws
    while True:
        try:
            async for message in websocket:
                await read_command(*jsonpickle.decode(message))
        except Exception as e:
            print(e)
            print("client has disconnected")
            break
    print("disconnected")


async def read_command(command, data):
    if command == 'msg_out':
        await client.send(fbchat.Message(text=data[0]), thread_id=data[1], thread_type=data[2])
        # return await websocket.recv()
    if command == 'get_convo':
        if data == "all":
            dict_convos = {k: v.get_dict() for k, v in conversations.items()}
            await send('rcv_all_convo', dict_convos)
           # return await websocket.recv()
        else:
            await send('rcv_convo', conversations[data].get_dict())
           # return await websocket.recv()


async def send(command, data):
    global websocket
    await websocket.send(jsonpickle.encode((command, data)))

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--start', action="store_true", help='start the server')
args = parser.parse_args()
if args.start:
    try:
        client = cli()
        client.loop.run_until_complete(init())
        client.listen()
        start_server = websockets.serve(relay, 'localhost', 15555)
        client.loop.run_until_complete(start_server)
        client.loop.run_forever()
    except KeyboardInterrupt:
        with open('session.json', 'w') as f:
            json.dump(client.get_session(), f)
