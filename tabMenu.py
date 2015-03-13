__author__ = 'chris.gardner'

from PySide import QtCore, QtGui
import os


def nonconsec_find(needle, haystack, anchored = False):
    """checks if each character of "needle" can be found in order (but not
    necessarily consecutivly) in haystack.
    For example, "mm" can be found in "matchmove", but not "move2d"
    "m2" can be found in "move2d", but not "matchmove"

    >>> nonconsec_find("m2", "move2d")
    True
    >>> nonconsec_find("m2", "matchmove")
    False

    Anchored ensures the first letter matches

    >>> nonconsec_find("atch", "matchmove", anchored = False)
    True
    >>> nonconsec_find("atch", "matchmove", anchored = True)
    False
    >>> nonconsec_find("match", "matchmove", anchored = True)
    True

    If needle starts with a string, non-consecutive searching is disabled:

    >>> nonconsec_find(" mt", "matchmove", anchored = True)
    False
    >>> nonconsec_find(" ma", "matchmove", anchored = True)
    True
    >>> nonconsec_find(" oe", "matchmove", anchored = False)
    False
    >>> nonconsec_find(" ov", "matchmove", anchored = False)
    True
    """

    if "[" not in needle:
        haystack = haystack.rpartition(" [")[0]

    if len(haystack) == 0 and len(needle) > 0:
        # "a" is not in ""
        return False

    elif len(needle) == 0 and len(haystack) > 0:
        # "" is in "blah"
        return True

    elif len(needle) == 0 and len(haystack) == 0:
        # ..?
        return True


    # Turn haystack into list of characters (as strings are immutable)
    haystack = [hay for hay in str(haystack)]

    if needle.startswith(" "):
        # "[space]abc" does consecutive search for "abc" in "abcdef"
        if anchored:
            if "".join(haystack).startswith(needle.lstrip(" ")):
                return True
        else:
            if needle.lstrip(" ") in "".join(haystack):
                return True

    if anchored:
        if needle[0] != haystack[0]:
            return False
        else:
            # First letter matches, remove it for further matches
            needle = needle[1:]
            del haystack[0]

    for needle_atom in needle:
        try:
            needle_pos = haystack.index(needle_atom)
        except ValueError:
            return False
        else:
            # Dont find string in same pos or backwards again
            del haystack[:needle_pos + 1]
    return True


class NodeWeights(object):
    def __init__(self, fname = None):
        self.fname = fname
        self._weights = {}

    def load(self):
        if self.fname is None:
            return

        def _load_internal():
            import json
            if not os.path.isfile(self.fname):
                print "Weight file does not exist"
                return
            f = open(self.fname)
            self._weights = json.load(f)
            f.close()

        # Catch any errors, print traceback and continue
        try:
            _load_internal()
        except Exception:
            print "Error loading node weights"
            import traceback
            traceback.print_exc()

    def save(self):
        if self.fname is None:
            print "Not saving node weights, no file specified"
            return

        def _save_internal():
            import json
            ndir = os.path.dirname(self.fname)
            if not os.path.isdir(ndir):
                try:
                    os.makedirs(ndir)
                except OSError, e:
                    if e.errno != 17: # errno 17 is "already exists"
                        raise

            f = open(self.fname, "w")
            # TODO: Limit number of saved items to some sane number
            json.dump(self._weights, fp = f)
            f.close()

        # Catch any errors, print traceback and continue
        try:
            _save_internal()
        except Exception:
            print "Error saving node weights"
            import traceback
            traceback.print_exc()

    def get(self, k, default = 0):
        if len(self._weights.values()) == 0:
            maxval = 1.0
        else:
            maxval = max(self._weights.values())
            maxval = max(1, maxval)
            maxval = float(maxval)

        return self._weights.get(k, default) / maxval

    def increment(self, key):
        self._weights.setdefault(key, 0)
        self._weights[key] += 1

class NodeModel(QtCore.QAbstractListModel):
    def __init__(self, mlist, weights, num_items = 15, filtertext = ""):
        super(NodeModel, self).__init__()

        self.weights = weights
        self.num_items = num_items

        self._all = mlist
        self._filtertext = filtertext

        # _items is the list of objects to be shown, update sets this
        self._items = []
        self.update()

    def set_filter(self, filtertext):
        self._filtertext = filtertext
        self.update()

    def update(self):
        filtertext = self._filtertext.lower()

        # Two spaces as a shortcut for [
        filtertext = filtertext.replace("  ", "[")

        scored = []
        for n in self._all:
            # Turn "3D/Shader/Phong" into "Phong [3D/Shader]"
            menupath = n['menupath'].replace("&", "")
            uiname = "%s [%s]" % (menupath.rpartition("/")[2], menupath.rpartition("/")[0])

            if nonconsec_find(filtertext, uiname.lower(), anchored=True):
                # Matches, get weighting and add to list of stuff
                score = self.weights.get(n['menupath'])

                scored.append({
                        'text': uiname,
                        'menupath': n['menupath'],
                        'menuobj': n['menuobj'],
                        'score': score})

        # Store based on scores (descending), then alphabetically
        s = sorted(scored, key = lambda k: (-k['score'], k['text']))

        self._items = s
        self.modelReset.emit()

    def rowCount(self, parent = QtCore.QModelIndex()):
        return min(self.num_items, len(self._items))

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            # Return text to display
            raw = self._items[index.row()]['text']
            return raw

        elif role == QtCore.Qt.DecorationRole:
            weight = self._items[index.row()]['score']

            hue = 0.4
            sat = weight

            if index.row() % 2 == 0:
                col = QtGui.QColor.fromHsvF(hue, sat, 0.9)
            else:
                col = QtGui.QColor.fromHsvF(hue, sat, 0.8)

            pix = QtGui.QPixmap(6, 12)
            pix.fill(col)
            return pix

        elif role == QtCore.Qt.BackgroundRole:
            return
            weight = self._items[index.row()]['score']

            hue = 0.4
            sat = weight ** 2 # gamma saturation to make faster falloff

            sat = min(1.0, sat)

            if index.row() % 2 == 0:
                return QtGui.QColor.fromHsvF(hue, sat, 0.9)
            else:
                return QtGui.QColor.fromHsvF(hue, sat, 0.8)
        else:
            # Ignore other roles
            return None

    def getorig(self, selected):
        # TODO: Is there a way to get this via data()? There's no
        # Qt.DataRole or something (only DisplayRole)

        if len(selected) > 0:
            # Get first selected index
            selected = selected[0]

        else:
            # Nothing selected, get first index
            selected = self.index(0)

        # TODO: Maybe check for IndexError?
        selected_data = self._items[selected.row()]
        return selected_data

class TabyLineEdit(QtGui.QLineEdit):
    pressed_arrow = QtCore.Signal(str)
    cancelled = QtCore.Signal()


    def event(self, event):
        """Make tab trigger returnPressed

        Also emit signals for the up/down arrows, and escape.
        """
        is_keypress = event.type() == QtCore.QEvent.KeyPress
        if is_keypress:
            print 'taby keyboard event!!'
            print event.key()


        if is_keypress and event.key() == QtCore.Qt.Key_Tab:
            # Can't access tab key in keyPressedEvent
            self.returnPressed.emit()
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Up:
            # These could be done in keyPressedEvent, but.. this is already here
            self.pressed_arrow.emit("up")
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Down:
            self.pressed_arrow.emit("down")
            return True

        elif is_keypress and event.key() == QtCore.Qt.Key_Escape:
            self.cancelled.emit()
            return True

        else:
            return super(TabyLineEdit, self).event(event)


class TabTabTabWidget(QtGui.QWidget):
    def __init__(self, on_create = None):
        super(TabTabTabWidget, self).__init__()

        self.setMinimumSize(200, 300)
        self.setMaximumSize(200, 300)

        # Store callback
        self.cb_on_create = on_create

        # Input box
        self.input = TabyLineEdit()

        # Node weighting
        self.weights = NodeWeights(os.path.expanduser("~/.nuke/tabtabtab_weights.json"))
        self.weights.load() # weights.save() called in close method

        nodes = [
            {'menuobj': 'one', 'menupath': '/something/one'},
            {'menuobj': 'two', 'menupath': '/something/two'},
            {'menuobj': 'three', 'menupath': '/something/three'},
        ]

        # List of stuff, and associated model
        self.things_model = NodeModel(nodes, weights = self.weights)
        self.things = QtGui.QListView()
        self.things.setModel(self.things_model)

        # Add input and items to layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.things)

        # Remove margins
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Update on text change
        self.input.textChanged.connect(self.update)

        # Reset selection on text change
        self.input.textChanged.connect(lambda: self.move_selection(where="first"))
        self.move_selection(where = "first") # Set initial selection

        # Create node when enter/tab is pressed, or item is clicked
        self.input.returnPressed.connect(self.create)
        self.things.clicked.connect(self.create)

        # When esc pressed, close
        self.input.cancelled.connect(self.hide)

        # Up and down arrow handling
        self.input.pressed_arrow.connect(self.move_selection)

    def event(self, event):
        """Make tab trigger returnPressed

        Also emit signals for the up/down arrows, and escape.
        """
        print 'event!'
        is_keypress = event.type() == QtCore.QEvent.KeyPress


        if is_keypress and event.key() == QtCore.Qt.Key_Escape:
            self.hide()



    def under_cursor(self):
        def clamp(val, mi, ma):
            return max(min(val, ma), mi)

        # Get cursor position, and screen dimensions on active screen
        cursor = QtGui.QCursor().pos()
        screen = QtGui.QDesktopWidget().screenGeometry(cursor)

        # Get window position so cursor is just over text input
        xpos = cursor.x() - (self.width()/2)
        ypos = cursor.y() - 13

        # Clamp window location to prevent it going offscreen
        xpos = clamp(xpos, screen.left(), screen.right() - self.width())
        ypos = clamp(ypos, screen.top(), screen.bottom() - (self.height()-13))

        # Move window
        self.move(xpos, ypos)

    def move_selection(self, where):
        if where not in ["first", "up", "down"]:
            raise ValueError("where should be either 'first', 'up', 'down', not %r" % (
                    where))

        first = where == "first"
        up = where == "up"
        down = where == "down"

        if first:
            self.things.setCurrentIndex(self.things_model.index(0))
            return

        cur = self.things.currentIndex()
        if up:
            new = cur.row() - 1
            if new < 0:
                new = self.things_model.rowCount() - 1
        elif down:
            new = cur.row() + 1
            count = self.things_model.rowCount()
            if new > count-1:
                new = 0

        self.things.setCurrentIndex(self.things_model.index(new))

    def event(self, event):
        """Close when window becomes inactive (click outside of window)
        """
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.close()
            return True
        else:
            return super(TabTabTabWidget, self).event(event)

    def update(self, text):
        """On text change, selects first item and updates filter text
        """
        self.things.setCurrentIndex(self.things_model.index(0))
        self.things_model.set_filter(text)

    def show(self):
        """Select all the text in the input (which persists between
        show()'s)

        Allows typing over previously created text, and [tab][tab] to
        create previously created node (instead of the most popular)
        """

        # Load the weights everytime the panel is shown, to prevent
        # overwritting weights from other Nuke instances
        self.weights.load()

        # Select all text to allow overwriting
        self.input.selectAll()
        self.input.setFocus()

        super(TabTabTabWidget, self).show()

    def close(self):
        """Save weights when closing
        """
        self.weights.save()
        self.hide()
        super(TabTabTabWidget, self).close()

    def create(self):
        # Get selected item
        selected = self.things.selectedIndexes()
        if len(selected) == 0:
            return

        thing = self.things_model.getorig(selected)

        # Store the full UI name of the created node, so it is the
        # active node on the next [tab]. Prefix it with space,
        # to disable substring matching
        if thing['text'].startswith(" "):
            prev_string = thing['text']
        else:
            prev_string = " %s" % thing['text']

        self.input.setText(prev_string)

        # Create node, increment weight and close
        self.close()