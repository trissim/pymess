#import fbchat_asyncio as fbchat
import fbchat
import asyncio

all_users = {}
all_messages = {}
conversations = {}

class conversation:
    def __init__(self,thread):
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
    
    def get_username(self,uid=None):
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
    def buffer_message(self,msg_uid):
        msg = all_messages[str(msg_uid)]
        if not msg.author in self.users:
            username = "You"
        else:
            username = self.get_username(uid=msg.author)
        self.buffer.append(username+":\n"+msg.text)
        print(self.buffer[-1])
    
    def create_groupname(self,style='short'):
        names = []
        users = [all_users[participant] for participant in self.thread.participants]
        if style == "short":
            names = [user.first_name for user in users]
        name = ", ".join(names[:2])
        if len(names) > 2:
            name = name + " + "+str(len(names[-1]))
        return name

loop = asyncio.get_event_loop()

async def get_user_infos(client,users):
    users = set(users)
    users_to_check = set(all_users.keys()) - users
    for user in users_to_check:
        all_users[user] = list((await client.fetch_user_info(user)).values())[0]

async def init_users(client):
    users = await client.fetch_all_users()
    for user in users:
        all_users[str(user.uid)] = user

async def init_conversations(client,conversations,threads):
    print("in init convo")
    conversations = {thread.uid:conversation(thread) for thread in threads}
    for convo in conversations.values():
        msgs = await client.fetch_thread_messages(convo.thread.uid)
        for msg in msgs:
           all_messages[str(msg.uid)] = msg
           convo.messages.append(msg.uid)
        convo.messages.reverse()
    return conversations

async def init_buffers(client, conversations):
    print("in init buffer")
    for convo in conversations.values():
        try:
            print("Convo name:",convo.convo_name())
        except KeyError as e:
            await get_user_infos(client,convo.users)
            convo.update()
        for msg_uid in convo.messages:
            convo.buffer_message(msg_uid)

async def init(conversations):
    client = fbchat.Client()
    await client.start("tristan6100@hotmail.com","Roxy6100!!")
    threads = await client.fetch_thread_list()
    await init_users(client)
    print("init convo")
    conversations = await init_conversations(client,conversations,threads)
    print("conversations:", conversations)
    print("init buffer")
    await init_buffers(client, conversations)
    for convo in conversations.values():
        print("Thread Name:",convo.convo_name())
        for msg in convo.buffer: print(msg)

client, conversations = loop.run_until_complete(init(conversations))

class cli(Client):
    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)
        all_messages[str(message_object.uid)] = message_object
        if not thread_id in conversations.keys():
            thread = list(self.fetch_thread_info(thread_id).values())[0]
            conversations.update(init_conversations(self,{},thread))
        else:
            conversations[str(thread_id)].messages.append(message_object.uid)
        log.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))


