import asyncio


@asyncio.coroutine
def render(app):
    if app.root.dirty:
        app.log("Rendering")
        app.stdscr.refresh()
        app.recalculate_windows()
        for box, win, pad in app.windows:
            win.refresh()
            x, y = box.upper_left
            dx, dy = box.lower_right
            pad.refresh(0, 0, y + 1, x + 1, dy - 2, dx - 2)
        app.root.dirty = False
    # I'd love the idea of "repeat this indefinitely" to be expressed in the
    # decorator used, but that might deny the ability to key it off particular
    # logic?
    app.loop.create_task(render(app))


@asyncio.coroutine
def quit(app):
    app.loop.stop()
