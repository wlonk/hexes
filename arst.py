#!/usr/bin/env python

# The basic imports:
import logging
import curses
from hexes import (
    Application,
    Box,
    Style,
)
from hexes.behaviors import quit

# We're going to use this in the logic below; not part of Hexes.
import subprocess


logging.basicConfig(filename='hexes.log', level=logging.DEBUG)

# Layout
#
# You can nest boxes indefinitely, though some layouts may fail on some screen
# sizes. You can specify text for boxes, whether that text should be flowed or
# treated as fixed, whether child boxes should be laid out horizontally or
# vertically, height and width for boxes, etc.
ls_box = Box()
root = Box(
    style=Style(
        layout=Style.Layout.Horizontal,
    ),
    children=(
        Box(
            children=(
                ls_box,
                Box(
                    style=Style(
                        height=3,
                    ),
                ),
            ),
        ),
        Box(
            style=Style(
                width=20,
            ),
        ),
    ),
)

# Logic
#
# Instantiate the application with the layout attached.
# Register any pre-defined behaviors you want (right now, that's only `quit`)
# using the same mechanism as custom behaviors, `app.on`.
app = Application(root=root)
app.on('q', quit)


#@app.on(curses.KEY_UP)
@app.on('j')
def scroll_up(app):
    app.log('in keyup')
    app.log('offset is {0}'.format(ls_box._text_offset))
    ls_box._text_offset -= 1
    app.root.dirty = True


#@app.on(curses.KEY_DOWN)
@app.on('k')
def scroll_down(app):
    app.log('in keydown')
    app.log('offset is {0}'.format(ls_box._text_offset))
    ls_box._text_offset += 1
    app.root.dirty = True


app.on(curses.KEY_UP, scroll_up)


# Define custom behavior with the `@app.on` decorator. This decorator
# requires an event identifier, which is either 'ready' or a key identifier
# as returned by `curses.window.getkey`
@app.on('ready')
def show_files(app):
    # For this example, we're just gonna output an `ls` of the local directory.
    ls = str(subprocess.check_output('ls'), 'utf-8')
    if ls_box.text != ls:
        ls_box.text = ls
    # To run a task forever, you have to tell it to schedule itself again:
    app.schedule(show_files)


# Run
#
# The context manager helps us clean up no matter what exceptional exit
# conditions we have.
with app:
    app.run()
