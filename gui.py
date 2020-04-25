from prompt_toolkit import Application
from prompt_toolkit import prompt
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.containers import VSplit, Window, HSplit
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()
@kb.add('c-q')
def exit_(event):
    """
    Pressing Ctrl-Q will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()


chat_buff = Buffer()  # Editable buffer.
input_buff = TextArea()


chat_container = HSplit([
    Window(content=BufferControl(buffer=chat_buff)),
    Window(width=30, height=1, char='-'),
    Window(content=BufferControl(buffer=input_buff)),
    ])
    
root_container = VSplit([
    # One window that holds the BufferControl with the default buffer on
    # the left.
    
    # A vertical line in the middle. We explicitly specify the width, to
    # make sure that the layout engine will not try to divide the whole
    # width by three for all these windows. The window will simply fill its
    # content by repeating this character.
    
    # Display the text 'Hello world' on the right.
    Window(content=FormattedTextControl(text='Hello world')),
    Window(width=1, char='|'),
    chat_container,
])
    

layout = Layout(root_container)

app = Application(key_bindings=kb, layout=layout, full_screen=True)
app.run() # You won't be able to Exit this app
