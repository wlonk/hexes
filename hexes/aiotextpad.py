import curses
import curses.textpad
from functools import partial
from .behaviors import _edit


class AsyncTextbox(curses.textpad.Textbox):
    """
    Editing widget using the interior of a window object.
    Supports the following Emacs-like key bindings:

    Ctrl-A      Go to left edge of window.
    Ctrl-B      Cursor left, wrapping to previous line if appropriate.
    Ctrl-D      Delete character under cursor.
    Ctrl-E      Go to right edge (stripspaces off) or end of line
                (stripspaces on).
    Ctrl-F      Cursor right, wrapping to next line when appropriate.
    Ctrl-G      Terminate, returning the window contents.
    Ctrl-H      Delete character backward.
    Ctrl-J      Terminate if the window is 1 line, otherwise insert newline.
    Ctrl-K      If line is blank, delete it, otherwise clear to end of line.
    Ctrl-L      Refresh screen.
    Ctrl-N      Cursor down; move down one line.
    Ctrl-O      Insert a blank line at cursor location.
    Ctrl-P      Cursor up; move up one line.

    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:

    KEY_LEFT = Ctrl-B, KEY_RIGHT = Ctrl-F, KEY_UP = Ctrl-P, KEY_DOWN = Ctrl-N
    KEY_BACKSPACE = Ctrl-h
    """
    def __init__(self, win, box, app, insert_mode=False):
        self.win = win
        self.box = box
        self.app = app
        self.insert_mode = insert_mode
        self.maxy, self.maxx = win.getmaxyx()
        self.maxy = self.maxy - 1
        self.maxx = self.maxx - 1
        self.stripspaces = 1
        self.lastcmd = None
        self.is_active = False
        self.characters = ""
        self._cursor = 0
        self.win.keypad(1)

    @property
    def cursor(self):
        return self._cursor

    @cursor.setter
    def cursor(self, val):
        self._cursor = self.bounded(val, 0, len(self.characters))

    @staticmethod
    def bounded(val, min_, max_):
        # @TODO unit tests for this.
        assert min_ < max_
        return min(
            max_,
            max(min_, val)
        )

    def edit(self, validate=None, callback=None):
        self.is_active = True
        self.app.schedule(
            partial(
                _edit,
                textbox=self,
                validate=validate,
                callback=callback,
            )
        )

    def ctrl_a(self, ch, x, y):
        self.win.move(y, 0)

    def ctrl_d(self, ch, x, y):
        self.win.delch()

    def ctrl_e(self, ch, x, y):
        if self.stripspaces:
            self.win.move(y, self._end_of_line(y))
        else:
            self.win.move(y, self.maxx)

    def ctrl_f(self, ch, x, y):
        self.cursor += 1
        return True

    def ctrl_g(self, ch, x, y):
        return 0

    def ctrl_j(self, ch, x, y):
        if self.maxy == 0:
            return 0
        elif y < self.maxy:
            self.win.move(y + 1, 0)

    def ctrl_k(self, ch, x, y):
        if x == 0 and self._end_of_line(y) == 0:
            self.win.deleteln()
        else:
            # first undo the effect of self._end_of_line
            self.win.move(y, x)
            self.win.clrtoeol()

    def ctrl_l(self, ch, x, y):
        self.win.refresh()

    def ctrl_n(self, ch, x, y):
        if y < self.maxy:
            self.win.move(y + 1, x)
            if x > self._end_of_line(y + 1):
                self.win.move(y + 1, self._end_of_line(y + 1))

    def ctrl_o(self, ch, x, y):
        self.win.insertln()

    def ctrl_p(self, ch, x, y):
        if y > 0:
            self.win.move(y - 1, x)
            if x > self._end_of_line(y - 1):
                self.win.move(y - 1, self._end_of_line(y - 1))

    def leftward_key(self, ch, x, y):
        if self.cursor > 0:
            self.cursor -= 1
            self.win.move(y, self.cursor)
        elif y == 0:
            pass
        elif self.stripspaces:
            self.win.move(y - 1, self._end_of_line(y - 1))
        else:
            self.win.move(y - 1, self.maxx)
        if ch in (curses.ascii.BS, curses.KEY_BACKSPACE):
            self.characters = (
                self.characters[:self.cursor]
                + self.characters[self.cursor + 1:]
            )
        return True

    def do_printable_char(self, ch, x, y):
        if y < self.maxy or x < self.maxx:
            self._insert_printable_char(ch)
        return True

    def _insert_printable_char(self, ch):
        # @TODO This doesn't do all the things of the super that it should.
        ch = chr(ch)
        self.characters = (
            self.characters[:self.cursor] + ch + self.characters[self.cursor:]
        )
        self.cursor += 1

        # Super:
        # (y, x) = self.win.getyx()
        # if y < self.maxy or x < self.maxx:
        #     if self.insert_mode:
        #         oldch = self.win.inch()
        #     # The try-catch ignores the error we trigger from some curses
        #     # versions by trying to write into the lowest-rightmost spot
        #     # in the window.
        #     try:
        #         self.win.addch(ch)
        #     except curses.error:
        #         pass
        #     if self.insert_mode:
        #         (backy, backx) = self.win.getyx()
        #         if curses.ascii.isprint(oldch):
        #             self._insert_printable_char(oldch)
        #             self.win.move(backy, backx)

    def do_command(self, ch):
        "Process a single editing command."
        y, x = self.win.getyx()
        self.lastcmd = ch
        leftward_keys = (
            curses.ascii.STX,
            curses.KEY_LEFT,
            curses.ascii.BS,
            curses.KEY_BACKSPACE,
        )
        rightward_keys = (
            curses.ascii.ACK,
            curses.KEY_RIGHT,
        )
        downward_keys = (
            curses.ascii.SO,
            curses.KEY_DOWN,
        )
        upward_keys = (
            curses.ascii.DLE,
            curses.KEY_UP,
        )
        # This is a tuple of 2-tuples of (predicate, action)
        the_big_map = (
            (lambda ch: curses.ascii.isprint(ch), self.do_printable_char),
            (lambda ch: ch == curses.ascii.SOH, self.ctrl_a),
            (lambda ch: ch in leftward_keys, self.leftward_key),
            (lambda ch: ch == curses.ascii.EOT, self.ctrl_d),
            (lambda ch: ch == curses.ascii.ENQ, self.ctrl_e),
            (lambda ch: ch in rightward_keys, self.ctrl_f),
            (lambda ch: ch == curses.ascii.BEL, self.ctrl_g),
            (lambda ch: ch == curses.ascii.NL, self.ctrl_j),
            (lambda ch: ch == curses.ascii.VT, self.ctrl_k),
            (lambda ch: ch == curses.ascii.FF, self.ctrl_l),
            (lambda ch: ch in downward_keys, self.ctrl_n),
            (lambda ch: ch == curses.ascii.SI, self.ctrl_o),
            (lambda ch: ch in upward_keys, self.ctrl_p),
        )

        ret = ch
        for i, (predicate, action) in enumerate(the_big_map):
            if predicate(ch):
                ret = action(ch, x, y)
                if ret is not None:
                    return ret
        return ret
