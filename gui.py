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
import sys

chat_area = True 

chat = ""
curr_chat = "me"
chats = {}
chats[curr_chat] = ''
def status_bar():
    return "logged in"

class convo:
    def __init__(self,name):
        self.name = name
        self.text = ""

conversations = []
for i in range(30):
    conversations.append(convo("user"+str(i)))

conversation = conversations[0]

kb = KeyBindings()

def vi_mode_to_cursor(mode):
    return {InputMode.NAVIGATION: 1, InputMode.REPLACE: 3}.get(mode, 5)

def get_input_mode(self):
    if sys.version_info[0] == 3:
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

@kb.add('tab')
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

@kb.add('c-q')
def exit_(event):
    event.app.exit()

def accept_message(input_buff):
    if input_buff.text != "":
        conversation.text += "Me:\n" + input_buff.text + "\n"
        log_buf.text = conversation.text
        input_win.height = 1

def auto_scroll(buff):
        buff.cursor_position = len(buff.text)-1

def resize_input(buff):
    input_win.height = buff.text.count('\n') + 1
    
@kb.add('enter')
def _(event):
    if event.app.layout.current_buffer == input_buf:
        accept_line(event)

def update_buffer():
    log_buf.text = conversation.text

def update_status():
    status_bar.content.text = HTML("<b>"+conversation.name+"</b>")

class convo_list:
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
            right_margins=[ScrollbarMargin(display_arrows=True),],
            width = 20,
            always_hide_cursor = True,
        )

    def _get_formatted_text(self):
        result = []
        for i, conversation in enumerate(conversations):
            name = conversation.name
            if i == self.selected_line:
                result.append([("[SetCursorPosition]", "")])
            result.append(name)
            result.append("\n")
        return merge_formatted_text(result)
    
    def _get_key_bindings(self):
        kb = KeyBindings()

        @kb.add("k")
        def _go_up(event) -> None:
            self.selected_line = (self.selected_line - 1) % len(conversations)
            app.output.hide_cursor()

        @kb.add("j")
        def _go_down(event) -> None:
            self.selected_line = (self.selected_line + 1) % len(conversations)
            app.output.hide_cursor()

        @kb.add('enter')
        def _(event):
            global conversation
            conversation = conversations[self.selected_line]
            update_status()
            update_buffer()
            toggle_convo_list()

        return kb

    def __pt_container__(self):
        return self.container

ctrls = {}
    
def get_toolbar(text):
   return FormattedTextToolbar(text=HTML("<b>"+text+"</b>"), style="bg:ansired fg:ansiblack")
def get_label(text):
   return Label(text=text,style="bg:ansiyellow fg:ansiblack", width = 10)

ctrls['tb'] = get_toolbar("Empty")
ctrls['lbl'] = get_label("Empty")

#message area
log_buf = Buffer(document=Document(chat))
log_win = Window(BufferControl(log_buf),wrap_lines=True)

#input area
input_buf = Buffer(document=Document())
input_win = Window(BufferControl(input_buf),height=1,wrap_lines=True)

#status bar
status_bar = FormattedTextToolbar(text=HTML("<b>Chatting with: " + conversation.name + "</b>"), style="bg:ansired fg:ansiblack")
status_label = Label(text="[ 00:29 ] ", width = 10)

#call backs
input_buf.accept_handler = accept_message
input_buf.on_text_changed += resize_input
log_buf.on_text_changed += auto_scroll
convos = convo_list()

chat_container = HSplit([
    log_win,
    status_bar,
    #ctrls['tb'],
    VSplit([
    #ctrls['lbl'],
    status_label,
    input_win])
    ])
    
root = VSplit([
    convos,
    chat_container,
])
    
style = Style.from_dict({"select-box cursor-line": "nounderline bg:ansired fg:ansiwhite"})

app = Application(editing_mode=EditingMode.VI, key_bindings=kb, layout=Layout(chat_container), full_screen=True, style = style)
app.layout.focus(input_buf) 
ViState._input_mode = InputMode.INSERT
ViState.input_mode = property(get_input_mode, set_input_mode)

log_buf.text = conversation.text

app.run() 
app.output.hide_cursor = lambda:None
