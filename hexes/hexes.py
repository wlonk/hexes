import curses
from math import floor
from utils import (
    Point,
    flatten,
)


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

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


class Box(object):
    def __init__(self, title=None, style=None, children=None):
        self.title = title
        self.style = style or Style()
        self._available_height = None
        self._available_width = None
        self.parent = None
        self.children = []
        children = children or []
        self.add_children(*children)

    def __str__(self):
        if self.title:
            return "Box: {}".format(self.title)
        return "Box"

    def __repr__(self):
        return "Box(title={s.title!r}, style={s.style!r}, children=[...])".format(s=self)

    @property
    def traverse_pre_order(self):
        return [self] + [x for x in flatten(c.traverse_pre_order for c in self.children)]

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
                    for sib in self.siblings
                    if type(sib.style.height) == int
                ])
                auto_sibs = [
                    sib
                    for sib in self.siblings
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
                    for sib in self.siblings
                    if type(sib.style.width) == int
                ])
                auto_sibs = [
                    sib
                    for sib in self.siblings
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
        return self.parent.children[self.parent.children.index(self):]

    @property
    def siblings(self):
        return self.older_siblings + self.younger_siblings

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
        self._registry = {}
        self.logs = []
        self.root = root
        if root is not None:
            self.recalculate_windows()

    def recalculate_windows(self):
        self.windows = []
        x, y = self.get_window_size()
        self.root.available_height = y
        self.root.available_width = x
        self.add_windows(*root.traverse_pre_order)

    def render(self):
        self.stdscr.refresh()
        for win in self.windows:
            win.refresh()

    def log(self, *args):
        msg = " ".join(map(str, args))
        self.logs.append(msg)

    def __enter__(self):
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)
        try:
            curses.curs_set(0)
        except:  # Gotta catch 'em all. We don't care that much abotu setitng curs to 0.
            pass
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
            self.recalculate_windows()
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
                style=Style(
                    min_height=10,
                    height=10,
                    layout=Style.Layout.Horizontal,
                ),
                children=(
                    Box(
                        title="AA",
                        style=Style(
                            min_height=2,
                        ),
                        children=(
                            Box(title="AAA"),
                            Box(title="AAB"),
                        ),
                    ),
                    Box(
                        title="AB",
                        style=Style(
                            min_height=2,
                        ),
                    ),
                ),
            ),
            Box(
                title="B",
                style=Style(
                    min_height=2,
                    height=5,
                ),
            ),
            Box(
                title="C",
                style=Style(min_height=2),
                children=(
                    Box(
                        title="CA",
                        style=Style(min_height=2),
                    ),
                    Box(
                        title="CB",
                        style=Style(min_height=2),
                        children=(
                            Box(
                                title="CBA",
                                style=Style(min_height=2),
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
