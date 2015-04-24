# -*- coding: utf-8 -*-
import curses
from utils import (
    Point,
    flatten,
)


class Box(object):
    def __init__(self, title=None, min_height=0, children=None):
        self.title = title
        self.min_height = min_height
        self.parent = None
        self.children = []
        children = children or []
        self.add_children(*children)

    def __str__(self):
        if self.title:
            return "Box: {}".format(self.title)
        return "Box"

    def __unicode__(self):
        return unicode(str(self))

    __repr__ = __str__

    @property
    def traverse_pre_order(self):
        return [self] + [x for x in flatten(c.whole_tree for c in self.children)]

    whole_tree = traverse_pre_order

    @property
    def height(self):
        if not self.children:
            ret = 2
        ret = sum(c.height for c in self.children) + 2
        return max(ret, self.min_height)

    @property
    def ancestors(self):
        if self.parent is not None:
            return [self.parent] + self.parent.ancestors
        return []

    @property
    def upper_left(self):
        if self.parent is not None:
            older_siblings = self.parent.children[:self.parent.children.index(self)]
            parent_height = self.parent.upper_left.y + 1
        else:
            older_siblings = []
            parent_height = 0
        return Point(
            len(self.ancestors),
            sum(os.height for os in older_siblings) + parent_height,
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
        self._registry = {}
        self.logs = []
        self.windows = []
        self.root = root
        if root is not None:
            self.add_windows(*root.whole_tree)

    def render(self):
        self.stdscr.refresh()
        if self.root:
            assert self.root.height <= self.get_window_size().y, "Root window too large."
        for win in self.windows:
            win.refresh()

    def log(self, *args):
        msg = " ".join(map(str, args))
        self.logs.append(msg)

    def __enter__(self):
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.curs_set(0)
        return self

    def __exit__(self, *args):
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def _process_key(self, key):
        if 0 <= key < 256 and chr(key) in self._registry:
            handler = self._registry[chr(key)]
            handler()
        if key == curses.KEY_RESIZE:
            self.render()

    def run(self):
        self.render()
        try:
            while True:
                self._process_key(self.stdscr.getch())
        except KeyboardInterrupt:
            return

    def quit(self):
        raise KeyboardInterrupt

    def get_window_size(self):
        y, x = self.stdscr.getmaxyx()
        return Point(x, y)

    def register(self, key, fn):
        if len(key) != 1:
            raise ValueError('Invalid key: {}'.format(repr(key)))
        self._registry[key] = fn

    def add_window(self, box):
        upper_left = box.upper_left
        win_x, win_y = self.get_window_size()
        x, y = upper_left
        columns = win_x - (x * 2)
        lines = box.height
        win = curses.newwin(lines, columns, y, x)
        win.border()
        if box.title:
            win.addstr(0, 1, box.title)
        self.windows.append(win)

    def add_windows(self, *boxes):
        for box in boxes:
            self.add_window(box)

if __name__ == "__main__":
    root = Box(
        title="Root",
        children=(
            Box(
                title="A",
                min_height=7,
                children=(
                    Box(title="AA"),
                    Box(title="AB"),
                ),
            ),
            Box(
                title="B",
                min_height=5,
            ),
            Box(
                title="C",
                children=(
                    Box(title="CA"),
                    Box(
                        title="CB",
                        children=(
                            Box(
                                title="CBA",
                                min_height=10,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    with Application(root=root) as app:
        app.register('q', app.quit)
        app.run()
    print('\n'.join(app.logs))
