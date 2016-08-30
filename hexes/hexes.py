"""
This module contains the core concepts of Hexes:

* :py:class:`.Style`
* :py:class:`.Box`
* :py:class:`.Application`
"""

import asyncio
import curses
import logging
from collections import defaultdict
from math import floor
from .aiotextpad import AsyncTextbox
from .utils import (
    Point,
    flatten,
    wrap_by_paragraph,
)
from .behaviors import render


class Style(object):
    """
    An object defining styles for a box.

    Keyword Arguments
    -----------------
    border_collapse : bool
        Whether child boxes should collapse adjacent borders into one, or not.
        Default: `True`.
    layout : Layout.Vertical or Layout.Horizontal
        Indicating whether to arrange child boxes in rows or columns.
        Default: `Layout.Horizontal`.
    height : int or Height.Auto
        Height in character cells, or "fit to available space".
    width : int or Width.Auto
        Width in character cells, or "fit to available space".
    flow : bool
        Indicating whether text in the box should be reflowed to fit, or
        printed literally. Default: `False`.
    """
    class Layout:
        Vertical = "vertical"
        Horizontal = "horizontal"

    class Height:
        Auto = "auto"

    class Width:
        Auto = "auto"

    border_collapse = True
    layout = Layout.Vertical
    min_height = 0
    height = Height.Auto
    min_width = 0
    width = Width.Auto
    flow = False

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


class Box(object):
    """
    An area drawn on the screen.

    Keyword Arguments
    -----------------
    title : str
        A short string shown in the upper left of the box.
    style : :py:class:`.Style`
        A bundle of style information.
    text : str
        The text to display in the box. It is auto-wrapped, and vertical
        scrolling is handled.
    editable : bool
        Whether the user can change the text in the box.
    children : list of :py:class:`.Box`
        A list of child boxes, to be laid out according to the `style`
        attribute.
    """
    def __init__(self,
                 title=None,
                 style=None,
                 text=None,
                 editable=False,
                 children=None):
        self.title = title
        self.style = style or Style()
        self.editable = editable
        self.parent = None
        self._text = text
        self._text_offset = 0
        self._available_height = None
        self._available_width = None
        self.children = []
        children = children or []
        self.add_children(*children)

    def __str__(self):
        if self.title:
            return "Box: {}".format(self.title)
        return "Box"

    def __repr__(self):
        return (
            "Box(title={s.title!r}, style={s.style!r}, children=[...])"
        ).format(s=self)

    def add_child(self, child):
        """
        Arguments
        ---------
        child : :py:class:`.Box`
            The box to append.
        """
        child.parent = self
        self.children.append(child)

    def add_children(self, *children):
        """
        Arguments
        ---------
        children : list of :py:class:`.Box`
            The boxes to append.
        """
        for child in children:
            self.add_child(child)

    @property
    def ancestors(self):
        """
        :returns: All the parent boxes, starting with the immediate parent, and
            ending with the root.
        :rtype: list of :py:class:`.Box`
        """

        if self.parent is not None:
            return [self.parent] + self.parent.ancestors
        return []

    @property
    def root(self):
        """
        :returns: The root box of the entire layout.
        :rtype: :py:class:`.Box`
        """
        def _helper(node):
            if node.parent is None:
                return node
            return _helper(node.parent)
        return _helper(self)

    @property
    def traverse_pre_order(self):
        """
        :returns: All boxes rooted at the current box, in pre-order.
        :rtype: list of :py:class:`.Box`
        """

        return [self] + [
            x for x in flatten(c.traverse_pre_order for c in self.children)
        ]

    @property
    def older_siblings(self):
        """
        :returns: All boxes that are children of the same parent, and earlier
            in that parent's children list than self.
        :rtype: list of :py:class:`.Box`
        """

        if self.parent is None:
            return []
        return self.parent.children[:self.parent.children.index(self)]

    @property
    def younger_siblings(self):
        """
        :returns: All boxes that are children of the same parent, and later in
            that parent's children list than self.
        :rtype: list of :py:class:`.Box`
        """

        if self.parent is None:
            return []
        # Plus one to exlude self.
        return self.parent.children[self.parent.children.index(self) + 1:]

    @property
    def siblings(self):
        """
        :returns: All boxes that are children of the same parent, minus self.
        :rtype: list of :py:class:`.Box`
        """

        return self.older_siblings + self.younger_siblings

    @property
    def siblings_including_self(self):
        """
        :returns: All boxes that are children of the same parent, inclusive of
            self.
        :rtype: list of :py:class:`.Box`
        """

        return self.older_siblings + [self] + self.younger_siblings

    def __available_dimension(self, main):
        if main == "height":
            full_dimension = Style.Layout.Horizontal
            divided_dimension = Style.Layout.Vertical
            auto_dimension = Style.Height.Auto
        elif main == "width":
            full_dimension = Style.Layout.Vertical
            divided_dimension = Style.Layout.Horizontal
            auto_dimension = Style.Width.Auto

        if getattr(self, '_available_{}'.format(main)) is not None:
            return getattr(self, '_available_{}'.format(main))
        if type(getattr(self.style, main)) == int:
            return getattr(self.style, main)
        if self.parent is not None:
            if self.parent.style.border_collapse:
                adjustment = 0
                small_adjustment = 0
            else:
                adjustment = 2
                small_adjustment = 1
            inside_main = (
                getattr(self.parent, 'available_{}'.format(main)) - adjustment
            )
            if self.parent.style.layout == full_dimension:
                return inside_main
            if self.parent.style.layout == divided_dimension:
                inside_main -= sum([
                    getattr(sib.style, main)
                    for sib in self.siblings_including_self
                    if type(getattr(sib.style, main)) == int
                ])
                auto_sibs = [
                    sib
                    for sib in self.siblings_including_self
                    if getattr(sib.style, main) == auto_dimension
                ]
                return (
                    floor(inside_main / len(auto_sibs) + 1) - small_adjustment
                )
        return 2

    @property
    def available_height(self):
        """
        Returns
        -------
        int
            The number of rows inside the parent box, accounting for the
            `border_collapse` setting.
        """

        return self.__available_dimension("height")

    @available_height.setter
    def available_height(self, val):
        self._available_height = val

    @property
    def available_width(self):
        """
        Returns
        -------
        int
            The number of columns inside the parent box, accounting for the
            `border_collapse` setting.
        """

        return self.__available_dimension("width")

    @available_width.setter
    def available_width(self, val):
        self._available_width = val

    def __dimension(self, main):
        if main == "height":
            auto_dimension = Style.Height.Auto
        else:
            auto_dimension = Style.Width.Auto

        if not self.children:
            required_main = 2

        if self.parent and self.parent.style.border_collapse:
            adjustment = 0
        else:
            adjustment = 2

        required_main = (
            sum(getattr(c, main) for c in self.children) + adjustment
        )
        if getattr(self.style, main) == auto_dimension:
            return getattr(self, "available_{}".format(main))
        if type(getattr(self.style, main)) == int:
            return getattr(self.style, main)
        return max(required_main, getattr(self.style, "min_{}".format(main)))

    @property
    def height(self):
        """
        Returns
        -------
        int
            Actual number of rows in the box, including any border.
        """

        return self.__dimension("height")

    @property
    def inner_height(self):
        """
        Returns
        -------
        int
            Actual number of rows in the box, excluding any border.
        """

        return self.height - 2

    @property
    def width(self):
        """
        Returns
        -------
        int
            Actual number of columns in the box, including any border.
        """

        return self.__dimension("width")

    @property
    def inner_width(self):
        """
        Returns
        -------
        int
            Actual number of columns in the box, excluding any border.
        """

        return self.width - 2

    @property
    def upper_left(self):
        """
        Returns
        -------
        int
            The location of the upper left corner of the box, when rendered.
        """

        if self.parent is not None:
            x, y = self.parent.upper_left
            layout = self.parent.style.layout
        else:
            x, y = -1, -1
            layout = Style.layout

        if self.older_siblings:
            elder_x, elder_y = self.older_siblings[-1].lower_right
        else:
            elder_x, elder_y = x, y

        if self.parent and self.parent.style.border_collapse:
            adjustment = 0
        else:
            adjustment = 1

        if layout == Style.Layout.Horizontal:
            point = Point(
                elder_x + adjustment - bool(self.older_siblings),
                y + adjustment,
            )
        else:
            point = Point(
                x + adjustment,
                elder_y + adjustment - bool(self.older_siblings),
            )
        return point

    @property
    def lower_right(self):
        """
        Returns
        -------
        int
            The location of the lower right corner of the box, when rendered.
        """

        x, y = self.upper_left
        return Point(
            x + self.width,
            y + self.height,
        )

    @property
    def text(self):
        """
        Returns
        -------
        str
            The inner text of the box. This may change if the box is editable.
        """

        return self._text

    @text.setter
    def text(self, val):
        self._text = val
        self.root.dirty = True

    def scroll(self, amount=1):
        """
        Move the visible contents of the box by `amount` rows.

        Keyword Arguments
        -----------------
        amount : int
            Number of rows to shift by. Defaults: `1`.
        """
        num_lines = self.text.count("\n")
        self._text_offset += amount
        self._text_offset = max(0, self._text_offset)
        self._text_offset = min(num_lines - 1, self._text_offset)
        self.root.dirty = True


class Application(object):
    """
    The enclosing Application object.

    Keyword Arguments
    -----------------
    root : :py:class:`.Box`
    """

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
        """
        Draw a box onto the screen.

        Arguments
        ---------
        box : :py:class:`.Box`
            The box to draw.
        """

        win_x, win_y = self.get_window_size()
        x, y = box.upper_left

        if box.parent is not None:
            columns = box.width
            lines = box.height
        else:
            columns = win_x
            lines = win_y

        win = curses.newwin(lines, columns, y, x)
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

        if box.editable:
            # We want to attach the textbox to the pad, not the window, because
            # the window has a border, and that means we capture the
            # box-drawing characters, and write on the border. UGLY.
            textbox = AsyncTextbox(pad, box, self)
        else:
            textbox = None

        # This should probably be a namedtuple
        self.windows.append((box, win, pad, textbox))

    def add_windows(self, *boxes):
        """
        Draw multiple boxes onto the screen.

        Arguments
        ---------
        boxes : :py:class:`.Box`
            The boxes to draw.
        """

        for box in boxes:
            self.add_window(box)

    def edit(self, box, callback=None):
        """
        Update the text contents of a particular box.

        Arguments
        ---------
        box : :py:class:`.Box`
            The (editable) box to trigger an edit on.

        Keyword Arguments
        -----------------
        callback : function in (self: :py:class:`.Application`)
            The continuation to run after processing the edit.
        """
        try:
            textbox = list(filter(lambda x: x[0] == box, self.windows))[0][3]
        except IndexError:
            return None
        self.log('editing')
        textbox.edit(callback=callback)

    def get_window_size(self):
        """
        :returns: the dimensions of the current terminal area.
        :rtype: :py:class:`.Point`
        """

        y, x = self.stdscr.getmaxyx()
        return Point(x, y)

    @property
    def has_active_textbox(self):
        """
        Returns
        -------
        bool
            Whether any box in the layout is editable and is currently active.
        """
        return any(
            getattr(textbox, 'is_active', False)
            for _, _, _, textbox in self.windows
        )

    def log(self, *args):
        """
        Log a message to the console behind the application.

        Arguments
        ---------
        args : str
            The strings to join with a space and log.
        """

        msg = " ".join(map(str, args))
        logging.info(msg)

    def on(self, event, func=None):
        """
        Bind a callback to an event.

        There are two ways to use this method: directly, and as a decorator.

        Directly::

            app.on('q', quit)

        for some function `quit`.

        As a decorator::

            @app.on('j')
            def scroll_down(app):
                ls_box.scroll(1)

        Arguments
        ---------
        event : str
            Either the event name to bind to, or a single character to listen
            for.

        Keyword Arguments
        -----------------
        func : function in (self: :py:class:`.Application`)
            The function to call on the bound event.
        """

        def decorator(fn):
            if not asyncio.iscoroutinefunction(fn):
                fn = asyncio.coroutine(fn)
            self._register(event, fn)
            return fn
        if func is None:
            return decorator
        return decorator(func)

    def recalculate_windows(self):
        """
        Redraw on window changes.
        """

        self.windows = []
        x, y = self.get_window_size()
        self.root.available_height = y
        self.root.available_width = x
        self.add_windows(*self.root.traverse_pre_order)

    def _register(self, event_id, fn):
        self._registry[event_id].append(fn)
        self.log("Run {} on {}".format(fn.__name__, event_id))

    def run(self):
        """
        Start the application loop and trigger the `ready` event.
        """

        self.loop.call_soon(self._process_key)
        self.schedule(render)
        for handler in self._registry['ready']:
            self.schedule(handler)
        try:
            self.loop.run_forever()
        except:
            self.loop.close()

    def schedule(self, coro_func):
        """
        Add a function to the application to do later.

        Arguments
        ---------
        coro_func : function in (self: :py:class:`.Application`)
            The function to add to the execution loop.
        """

        self.loop.create_task(coro_func(self))

    def _process_key(self):
        try:
            if self.has_active_textbox:
                pass
            else:
                key = self.stdscr.getkey()
                for handler in self._registry[key]:
                    self.schedule(handler)
        except curses.error:
            pass
        finally:
            self.loop.call_later(0.1, self._process_key)
