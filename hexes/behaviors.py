import asyncio
from functools import partial


@asyncio.coroutine
def render(app):
    if app.root.dirty:
        app.log("Rendering")
        app.stdscr.refresh()
        app.recalculate_windows()
        for box, win, pad, textbox in app.windows:
            win.refresh()
            x, y = box.upper_left
            dx, dy = box.lower_right
            pad.refresh(box._text_offset, 0, y + 1, x + 1, dy - 2, dx - 2)
        app.root.dirty = False
    # I'd love the idea of "repeat this indefinitely" to be expressed in the
    # decorator used, but that might deny the ability to key it off particular
    # logic?
    app.schedule(render)


@asyncio.coroutine
def quit(app):
    app.loop.stop()


@asyncio.coroutine
def _edit(app, textbox, validate, callback):
    ch = textbox.win.getch()
    if validate:
        ch = validate(ch)
    if not textbox.do_command(ch):
        textbox.is_active = False
        textbox.box.text = ''
        if callable(callback):
            task = partial(
                callback,
                textbox=textbox,
                characters=textbox.characters,
            )
            app.schedule(task)
    else:
        textbox.box.text = textbox.characters
        app.schedule(
            partial(
                _edit,
                textbox=textbox,
                validate=validate,
                callback=callback,
            )
        )
