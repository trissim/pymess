from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.widgets import Frame, FormattedTextToolbar, Label
from prompt_toolkit.layout.containers import VSplit, Window, HSplit
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout import FormattedTextControl
from prompt_toolkit.formatted_text import HTML, merge_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.named_commands import accept_line
from prompt_toolkit.key_binding.bindings import scroll
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.key_binding.vi_state import InputMode, ViState
from prompt_toolkit.styles import Style
from prompt_toolkit.output import Output
from collections import namedtuple
from fbchat import Message
import fbserver
import websockets
import fbchat
import pickle
import jsonpickle
import comms
import sys
import pymess
import asyncio
from collections import OrderedDict
import tracemalloc

tracemalloc.start()

conversations = {}
curr_convo = None
chat_area = True
kb = KeyBindings()
app = None
ws_handler = None


class handler:

    def __init__(self, URL):
        self.ws = None
        self.URL = URL

    async def connect(self):
        self.ws = await websockets.connect(self.URL)

    async def listen(self):
        while True:
            try:
                async for message in self.ws:
                    # print(type(read_command((*jsonpickle.decode(message)))))
                    read_command(*jsonpickle.decode(message))
            except Exception as e:
                print(e)
                print("Lost connection to server")
                break

    async def command(self, cmd):
        await self.ws.send(jsonpickle.encode(cmd))


def read_command(command, data):
    if command == 'rcv_all_convo':
        update_conversation(list(data.values()))
    if command == 'rcv_convo':
        update_conversation(data)


def update_conversation(recv_conversations):
    global conversations
    global curr_convo
    global log_buf
    if type(recv_conversations) is not list:
        recv_conversations = [recv_conversations]
    for conversation in recv_conversations:
        Conversation = namedtuple('Conversation', list(
            conversation.keys()))
        convo_obj = Conversation(**conversation)
        if curr_convo is None:
            curr_convo = convo_obj
        conversations.update({convo_obj.thread.uid: convo_obj})
        if curr_convo.thread.uid == convo_obj.thread.uid:
            curr_convo = convo_obj
            update_buffer()
            update_status()
            auto_scroll(log_buf)
    return


def vi_mode_to_cursor(mode):
    return {InputMode.NAVIGATION: 1, InputMode.REPLACE: 3}.get(mode, 5)


def get_input_mode(self):
    if sys.version_info[0] == 3:
        global app
        # Decrease input flush timeout from 500ms to 10ms.
        from prompt_toolkit.application.current import get_app
        app = get_app()
        app.ttimeoutlen = 0.01
    return self._input_mode


def toggle_convo_list():
    global chat_area
    if chat_area:
        app.layout = Layout(root)
        app.layout.focus(convos)
        chat_area = False
        change_cursor(1)
    else:
        app.layout = Layout(chat_container)
        app.layout.focus(input_buf)
        chat_area = True
        change_cursor(vi_mode_to_cursor(get_input_mode))


@ kb.add('tab')
def toggle_convo_list_(event):
    toggle_convo_list()


def change_cursor(shape):
    cursor = "\x1b[{} q".format(shape)
    if hasattr(sys.stdout, '_cli'):
        write = sys.stdout._cli.output.write_raw
    else:
        write = sys.stdout.write
    write(cursor)
    sys.stdout.flush()


def set_input_mode(self, mode):
    shape = {InputMode.NAVIGATION: 1, InputMode.REPLACE: 3}.get(mode, 5)
    change_cursor(shape)
    self._input_mode = mode


def vi_movement_mode(event):
    event.cli.key_processor.feed(KeyPress(Keys.Escape))


@ kb.add('c-q')
def exit_(event):
    event.app.exit()


def accept_message(input_buff):
    if input_buff.text != "":
        input_win.height = 1
        asyncio.ensure_future(
            ws_handler.command(("msg_out", [
                input_buff.text, curr_convo.thread.uid, curr_convo.thread.type])))
#            ws_handler.command(('get_convo', 'all')))
#        asyncio.get_event_loop().create_task(ws_handler.command(("msg_out", [
#            input_buff.text, curr_convo.thread.uid, curr_convo.thread.type])))


def auto_scroll(buff):
    buff.cursor_position = len(buff.text)-1


def resize_input(buff):
    input_win.height = buff.text.count("\n") + 1


@ kb.add('enter')
def _(event):
    if event.app.layout.current_buffer == input_buf:
        accept_line(event)
        event.app.invalidate()


def update_buffer():
    log_buf.text = "\n".join(curr_convo.buffer)


def update_status():
    status_bar.content.text = HTML("<b>"+curr_convo.name+"</b>")


class convo_list_widget:
    def __init__(self):
        self.selected_line = 0
        self.container = Window(
            content=FormattedTextControl(
                text=self._get_formatted_text,
                focusable=True,
                key_bindings=self._get_key_bindings(),
            ),
            style="class:select-box",
            cursorline=True,
            right_margins=[ScrollbarMargin(display_arrows=True), ],
            width=20,
            always_hide_cursor=True,
        )

    def _get_formatted_text(self):
        result = []
        for i, convs in enumerate(conversations.values()):
            name = convs.name
            if i == self.selected_line:
                result.append([("[SetCursorPosition]", "")])
            result.append(name)
            result.append("\n")
        return merge_formatted_text(result)

    def _get_key_bindings(self):
        kb = KeyBindings()

        @ kb.add("k")
        def _go_up(event) -> None:
            self.selected_line = (self.selected_line - 1) % len(conversations)
            app.output.hide_cursor()

        @ kb.add("j")
        def _go_down(event) -> None:
            self.selected_line = (self.selected_line + 1) % len(conversations)
            app.output.hide_cursor()

        @ kb.add('enter')
        def _(event):
            global curr_convo
            curr_convo = list(conversations.values())[self.selected_line]
            update_status()
            update_buffer()
            toggle_convo_list()

        return kb

    def __pt_container__(self):
        return self.container


root = None
chat_container = None
app = None
log_buf = None
log_win = None
input_buf = None
input_win = None
convos = None
status_bar = None
status_label = None
client = None


async def init():
    global root
    global chat_container
    global app
    global log_buf
    global log_win
    global input_buf
    global input_win
    global convos
    global status_bar
    global status_label
    global client
    global convo_stack
    global websocket
    global app
    global uri
    global websocket
    global ws_handler

    uri = "ws://localhost:15555"
    ws_handler = handler(uri)
    await ws_handler.connect()

    # message area
    log_buf = Buffer(document=Document())
    log_win = Window(BufferControl(log_buf), wrap_lines=True)

    # input area
    input_buf = Buffer(document=Document())
    input_win = Window(BufferControl(input_buf), height=1, wrap_lines=True)

    # status bar
    status_bar = FormattedTextToolbar(
        text=HTML("<b>Chatting with: Loading </b>"), style="bg:ansired fg:ansiblack")
    status_label = Label(text="[ 00:29 ] ", width=10)

    # call backs
    input_buf.accept_handler = accept_message
    input_buf.on_text_changed += resize_input
    log_buf.on_text_changed += auto_scroll
    convos = convo_list_widget()

    chat_container = HSplit([
        log_win,
        status_bar,
        VSplit([
            status_label,
            input_win])
    ])

    root = VSplit([
        convos,
        chat_container,
    ])

    style = Style.from_dict(
        {"select-box cursor-line": "nounderline bg:ansired fg:ansiwhite"})

    app = Application(editing_mode=EditingMode.VI, key_bindings=kb, layout=Layout(
        chat_container), full_screen=True, style=style)
    app.invalidate()
    app.layout.focus(input_buf)
    ViState._input_mode = InputMode.INSERT
    ViState.input_mode = property(get_input_mode, set_input_mode)

    asyncio.ensure_future(
        ws_handler.listen())
    asyncio.ensure_future(
        ws_handler.command(('get_convo', 'all')))

    auto_scroll(log_buf)
    await app.run_async()
