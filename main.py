#!/bin/python3
import asyncio
import fbchat
import websockets
import gui

all_users = {}
all_messages = {}
conversations = {}

loop = asyncio.get_event_loop()
loop.run_until_complete(gui.init())
