import asyncio
import curses
import logging
from collections import defaultdict
from math import floor
from .utils import (
    Point,
    flatten,
    wrap_by_paragraph,
)
from .behaviors import render


class Style(object):
    class Layout:
        Vertical = "vertical"
        Horizontal = "horizontal"

    class Height:
        Auto = "auto"

    class Width:
        Auto = "auto"

    layout = Layout.Vertical
    min_height = 0
    height = Height.Auto
    min_width = 0
    width = Width.Auto
    flow = False

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


class Box(object):
    def __init__(self, title=None, style=None, text=None, children=None):
        self.title = title
        self.style = style or Style()
        self.parent = None
        self._text = text
        self._available_height = None
        self._available_width = None
        self.children = []
        children = children or []
        self.add_children(*children)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, val):
        self._text = val
        self.root.dirty = True

    def __str__(self):
        if self.title:
            return "Box: {}".format(self.title)
        return "Box"

    def __repr__(self):
        return (
            "Box(title={s.title!r}, style={s.style!r}, children=[...])"
        ).format(s=self)

    @property
    def traverse_pre_order(self):
        return [self] + [
            x for x in flatten(c.traverse_pre_order for c in self.children)
        ]

    @property
    def root(self):
        def _helper(node):
            if node.parent is None:
                return node
            return _helper(node.parent)
        return _helper(self)

    @property
    def available_height(self):
        if self._available_height is not None:
            return self._available_height
        if type(self.style.height) == int:
            return self.style.height
        if self.parent is not None:
            inside_height = self.parent.available_height - 2
            if self.parent.style.layout == Style.Layout.Horizontal:
                return inside_height
            if self.parent.style.layout == Style.Layout.Vertical:
                inside_height -= sum([
                    sib.style.height
                    for sib in self.siblings_including_self
                    if type(sib.style.height) == int
                ])
                auto_sibs = [
                    sib
                    for sib in self.siblings_including_self
                    if sib.style.height == Style.Height.Auto
                ]
                return floor(inside_height / len(auto_sibs) + 1) - 1
        return 2

    @available_height.setter
    def available_height(self, val):
        self._available_height = val

    @property
    def available_width(self):
        if self._available_width is not None:
            return self._available_width
        if type(self.style.width) == int:
            return self.style.width
        if self.parent is not None:
            inside_width = self.parent.available_width - 2
            if self.parent.style.layout == Style.Layout.Vertical:
                return inside_width
            if self.parent.style.layout == Style.Layout.Horizontal:
                inside_width -= sum([
                    sib.style.width
                    for sib in self.siblings_including_self
                    if type(sib.style.width) == int
                ])
                auto_sibs = [
                    sib
                    for sib in self.siblings_including_self
                    if sib.style.width == Style.Width.Auto
                ]
                return floor(inside_width / len(auto_sibs) + 1) - 1
        return 2

    @available_width.setter
    def available_width(self, val):
        self._available_width = val

    @property
    def height(self):
        if not self.children:
            required_height = 2
        required_height = sum(c.height for c in self.children) + 2
        if self.style.height == Style.Height.Auto:
            return self.available_height
        if type(self.style.height) == int:
            return self.style.height
        return max(required_height, self.style.min_height)

    @property
    def inner_height(self):
        return self.height - 2

    @property
    def width(self):
        if not self.children:
            required_width = 2
        required_width = sum(c.width for c in self.children) + 2
        if self.style.width == Style.Width.Auto:
            return self.available_width
        if type(self.style.width) == int:
            return self.style.width
        return max(required_width, self.style.min_width)

    @property
    def inner_width(self):
        return self.width - 2

    @property
    def ancestors(self):
        if self.parent is not None:
            return [self.parent] + self.parent.ancestors
        return []

    @property
    def older_siblings(self):
        if self.parent is None:
            return []
        return self.parent.children[:self.parent.children.index(self)]

    @property
    def younger_siblings(self):
        if self.parent is None:
            return []
        # Plus one to exlude self.
        return self.parent.children[self.parent.children.index(self) + 1:]

    @property
    def siblings(self):
        return self.older_siblings + self.younger_siblings

    @property
    def siblings_including_self(self):
        return self.older_siblings + [self] + self.younger_siblings

    @property
    def upper_left(self):
        if self.parent is not None:
            x, y = self.parent.upper_left
            layout = self.parent.style.layout
        else:
            x, y = -1, -1
            layout = Style.layout

        if layout == Style.Layout.Horizontal:
            point = Point(
                sum(os.width for os in self.older_siblings) + x + 1,
                y + 1,
            )
        else:
            point = Point(
                x + 1,
                sum(os.height for os in self.older_siblings) + y + 1,
            )
        return point

    @property
    def lower_right(self):
        x, y = self.upper_left
        return Point(
            x + self.width,
            y + self.height,
        )

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def add_children(self, *children):
        for child in children:
            self.add_child(child)


class Application(object):
    def __init__(self, root=None):
        self.stdscr = curses.initscr()
        self._registry = defaultdict(list)
        self.root = root
        self.loop = asyncio.get_event_loop()
        if root is not None:
            self.recalculate_windows()
            self.root.dirty = True

    def __enter__(self):
        logging.basicConfig(
            filename='hexes.log',
            level=logging.DEBUG,
        )
        self.log("=" * 80)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        self.stdscr.nodelay(1)
        try:
            curses.curs_set(0)
        except:
            # We don't care that much about setitng curs to 0.
            pass
        return self

    def __exit__(self, *args):
        self.loop.close()
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def add_window(self, box):
        win_x, win_y = self.get_window_size()
        x, y = box.upper_left

        if box.parent is not None:
            if box.parent.style.layout == Style.Layout.Horizontal:
                columns = box.width
                lines = box.parent.height - 2
            else:
                columns = box.parent.width - 2
                lines = box.height
        else:
            columns = win_x
            lines = win_y

        win = curses.newwin(lines, columns, y, x)
        # Attach a pad to the window, to allow text overflow.
        pad = curses.newpad(box.inner_width, 1000)
        win.border()
        if box.title:
            win.addstr(0, 1, box.title)
        if box.text:
            if box.style.flow:
                text = wrap_by_paragraph(box.text, width=box.inner_width)
            else:
                text = box.text
            pad.addstr(0, 0, text)
        self.windows.append((box, win, pad))

    def add_windows(self, *boxes):
        for box in boxes:
            self.add_window(box)

    def get_window_size(self):
        y, x = self.stdscr.getmaxyx()
        return Point(x, y)

    def log(self, *args):
        msg = " ".join(map(str, args))
        logging.info(msg)

    def on(self, event):
        def decorator(fn):
            if not asyncio.iscoroutinefunction(fn):
                fn = asyncio.coroutine(fn)
            self.register(event, fn)
            return fn
        return decorator

    def recalculate_windows(self):
        self.windows = []
        x, y = self.get_window_size()
        self.root.available_height = y
        self.root.available_width = x
        self.add_windows(*self.root.traverse_pre_order)

    def register(self, event_id, fn):
        self._registry[event_id].append(fn)
        self.log("Run {} on {}".format(fn.__name__, event_id))

    def run(self):
        self.loop.call_soon(self.process_key)
        self.loop.create_task(render(self))
        for handler in self._registry['ready']:
            self.loop.create_task(handler(self))
        try:
            self.loop.run_forever()
        except:
            self.loop.close()

    def process_key(self):
        try:
            key = self.stdscr.getkey()
            for handler in self._registry[key]:
                self.loop.create_task(handler(self))
        except curses.error:
            pass
        finally:
            self.loop.call_later(0.1, self.process_key)
