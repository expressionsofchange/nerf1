"""
Vim-like interface for single-line editing.

This is not supposed to be have feature-parity with Vim; rather it's supposed to have just those features that I
personally have come to depend on.

# Python Generators

The below is implemented using Python generators/coroutines.

Some hints as to how this works:

`yield from` may be used to decompose generators; The passed parameters and returned value may be of any type that's
useful to you in the process of decomposition. This may contain `(text, cursor_pos)` info, but only if useful.

`yield` forms a direct interface between "the I/O" (screen, keyboard) and the yielding location. The yielding location
knows the latest state to be _output_ and communicates this; it yields control waiting for new _inputs_.

This is independent of choices made in the decomposition of the functions. From the perspective of the "yielding
location" this interface looks like this:

* You must always yield the current state `(text, cursor_pos)`.
* a `key` will be sent to you once control returns. (For the interface/type of 'sent keys' we use
    `generalized_key_press`, i.e. "Kivy with some changes".)


Are generators the right abstraction here? I think so: they allow for a linear-style of writing "I will wait until a new
keypress", without resorting to multi-threading.  A single-thread rewrite without generators would need extensive
callbacks, which hinders understanding. Of course, you do need to understand generators to be able to understand the
current version.
"""

from copy import copy


# Sigma.done enum
NOT_DONE = 0
DONE_SAVE = 1
DONE_CANCEL = 2


class Sigma(object):
    """A class encapsulating the state of a single-line vim editor.
    Because we have several similar such classes, I chose the meaningless name "sigma". Once this class grows or shrinks
    a better name will probably emerge.
    """

    def __init__(self, text, cursor_pos, done=NOT_DONE, last_ft=None, clipboard=""):
        # As it stands, the "last typed keys" are not part of the sigma;
        # This is not motivated by an overarching understanding/philosophy of what the sigma should be, but rather by
        # what looked good while creating the first version.

        self.text = text
        self.cursor_pos = cursor_pos
        self.done = done
        self.last_ft = last_ft
        self.clipboard = clipboard

    def set(self, **kwargs):
        """Creates a copy of the Sigma, with some values (as provided) changed."""
        result = copy(self)
        for key, value in kwargs.items():
            setattr(result, key, value)
        return result

    def __repr__(self):
        # convenience method; mostly for doctests
        return str((self.text, self.cursor_pos))


MOVE_TO_CHAR_KEYS = ['f', 'F', 't', 'T']
MOTION_KEYS = MOVE_TO_CHAR_KEYS + ['h', 'l', 'left', 'right', '$', '0', ';', ',']


def accumulate_sent(generator):
    # I've asked "the internet" for a better version of this:
    # https://stackoverflow.com/questions/42094633/how-to-observe-log-values-sent-to-a-python-generator

    sent_values = []

    try:
        generator_value = generator.send(None)

        while True:
            sent_value = yield generator_value
            sent_values.append(sent_value)
            generator_value = generator.send(sent_value)

    except StopIteration as e:
        return (e.value, sent_values)


class Vim(object):
    """
    >>> vim = Vim('some text to edit', 0)
    >>> vim.send('2')
    >>> vim.send('d')
    >>> vim.send('f')
    >>> vim.send('e')
    >>> vim.text
    'xt to edit'
    """

    def __init__(self, text, cursor_pos):
        # tree widgets use only (text, cursor_pos); we do not expose the full sigma
        sigma = Sigma(text, cursor_pos)

        self.v = normal_mode_loop(sigma)
        self.send(None)

    def send(self, key):
        self.sigma = self.v.send(key)

        # tree widgets use only (text, cursor_pos); we do not expose the full sigma
        self.text = self.sigma.text
        self.cursor_pos = self.sigma.cursor_pos
        self.done = self.sigma.done


def normal_mode_loop(sigma):
    prev_sent_keys = []

    # For un/re-doing, we remember (state, cursor_before, cursor_after) for each unique text. When we undo for a state
    # n, we go back to state n-1, and put the cursor where it was right before state n got created.
    # When redoing state n, we go to that state and put the cursor where it was right after the state was created.
    TEXT, CURSOR_BEFORE, CURSOR_AFTER = 0, 1, 2
    states = [(sigma.text, 0, sigma.cursor_pos)]
    undo_top = 0

    while True:
        key = yield sigma

        if key == 'u':
            if undo_top == 0:
                continue

            undo_to_text = states[undo_top - 1][TEXT]
            undo_to_cursor_pos = states[undo_top][CURSOR_BEFORE]

            # Note: We don't go fully back in time; only the text and cursor_pos are restored
            sigma = sigma.set(text=undo_to_text, cursor_pos=undo_to_cursor_pos)

            undo_top -= 1
            continue

        if key == 'r':
            if undo_top >= len(states) - 1:
                continue

            undo_top += 1

            redo_to_text = states[undo_top][TEXT]
            redo_to_cursor_pos = states[undo_top][CURSOR_AFTER]

            sigma = sigma.set(text=redo_to_text, cursor_pos=redo_to_cursor_pos)

            continue

        one_command = accumulate_sent(normal_mode(key, sigma, prev_sent_keys))

        new_sigma, further_sent_keys = yield from one_command
        sent_keys = [key] + further_sent_keys

        if new_sigma.text != sigma.text:
            if undo_top < len(states) - 1:
                # do-after-undo truncates history
                states = states[:undo_top + 1]

            # We take text-change to mean: something can be undone.
            states.append((new_sigma.text, sigma.cursor_pos, new_sigma.cursor_pos))
            undo_top = len(states) - 1

            if sent_keys != ['.']:
                # We take text-change to mean: Some command has succesfully executed. (TBH, I think the real Vim does
                # this differently, as evidenced by e.g. pressing 'i', 'escape', '.'). If we want to reproduce that
                # behavior, we need `normal_mode` to tell us whether a command was executed.

                # '.' is ignored; we the last command should never be "repeat last command".
                prev_sent_keys = sent_keys

        sigma = new_sigma


def normal_mode(key, sigma, sent_keys):
    """
    Performs 1 normal_mode action.

    The return type is: `sigma`. This is a necessary consequence of the requirement to chain operations: i.e.  we need a
    value to pass into the next call. (We don't need to return `sent_keys` ourselves: `normal_mode_loop` logs those for
    us.  Our return-value is _not_ a necessary consequence of the 'yield interface' (receive keyspresses by yielding the
    current state), despite being the same.
    """

    count = 1

    if key in ['escape', 'enter', 'numpadenter']:
        # Note: `normal_mode` and `normal_mode_loop` do not actually stop when they're done; they simply signal the
        # actual UI element which controls them to do a cleanup, but there is nothing (theoretically) preventing such an
        # element to say "carry on".
        return sigma.set(done=DONE_SAVE)

    if key in ['Q']:
        return sigma.set(done=DONE_CANCEL)

    if key.isdigit() and key != '0':
        key, count = yield from numeral(sigma, key)

    if key in MOTION_KEYS:
        motion_result = yield from motion(sigma, key, count)
        if motion_result is None:
            return sigma

        cursor_pos, inclusive_, last_ft = motion_result
        return sigma.set(cursor_pos=cursor_pos, last_ft=last_ft)

    if key in ['.']:
        nm = normal_mode(sent_keys[0], sigma, sent_keys)
        next(nm)
        for key in sent_keys[1:]:
            sigma = nm.send(key)
        return sigma

    if key in ['i', 'a', 'I', 'A']:
        cursor_pos = sigma.cursor_pos
        if key == 'a':
            # append (but don't but the cursor outside the text)
            cursor_pos = min(cursor_pos + 1, len(sigma.text))
        elif key == 'I':
            cursor_pos = 0
        elif key == 'A':
            cursor_pos = len(sigma.text)

        sigma = yield from insert_mode(sigma.set(cursor_pos=cursor_pos))
        return sigma

    if key in ['y']:
        motion_key = yield sigma

        motion_result = yield from motion(sigma, motion_key, count)
        if motion_result is None:
            return sigma

        yank_to_cursor_pos, yank_inclusive, last_ft = motion_result

        yank_to_cursor_pos += (1 if yank_inclusive else 0)

        yanked = ibeam_slice(sigma.text, sigma.cursor_pos, yank_to_cursor_pos)
        sigma = sigma.set(last_ft=last_ft, clipboard=yanked)

        return sigma

    if key in ['d', 'c']:
        motion_key = yield sigma

        motion_result = yield from motion(sigma, motion_key, count)
        if motion_result is None:
            return sigma

        delete_to_cursor_pos, delete_inclusive, last_ft = motion_result

        # AFAIU, inclusive=True can be simply translated into ibeam-curosr +=1. (This is slightly surprising for the
        # deletions in leftward direction, because in that case "inclusive" means "don't delete", but it's per spec).
        # We just have to make sure to do this only for deletions, not regular movement.
        delete_to_cursor_pos += (1 if delete_inclusive else 0)

        yanked = ibeam_slice(sigma.text, sigma.cursor_pos, delete_to_cursor_pos)
        text, cursor_pos = ibeam_delete(sigma.text, sigma.cursor_pos, delete_to_cursor_pos)
        sigma = sigma.set(text=text, cursor_pos=cursor_pos, last_ft=last_ft, clipboard=yanked)

        if key == 'c':
            sigma = yield from insert_mode(sigma)

        return sigma

    if key in ['D', 'C']:
        yanked = ibeam_slice(sigma.text, sigma.cursor_pos, len(sigma.text))
        text, cursor_pos = ibeam_delete(sigma.text, sigma.cursor_pos, len(sigma.text))
        sigma = sigma.set(text=text, cursor_pos=cursor_pos, clipboard=yanked)

        if key == 'C':
            sigma = yield from insert_mode(sigma)
        else:
            # meh... this is basically a correction on the missing block_delete() above; better would be to have the +1
            # in the other branch.
            sigma = sigma.set(cursor_pos=sigma.cursor_pos - 1)

        return sigma

    if key in ['x']:
        yanked = ibeam_slice(sigma.text, sigma.cursor_pos, sigma.cursor_pos + count)
        text, cursor_pos = block_delete(sigma.text, sigma.cursor_pos, sigma.cursor_pos + count - 1)
        return sigma.set(text=text, cursor_pos=cursor_pos, clipboard=yanked)

    if key in ['p', 'P']:
        text, cursor_pos = ibeam_insert(sigma.text, sigma.cursor_pos + (1 if key == 'p' else 0), sigma.clipboard)
        return sigma.set(text=text, cursor_pos=cursor_pos)

    if key in ['~']:
        text, cursor_pos = sigma.text, sigma.cursor_pos
        for i in range(count):
            text = text[:cursor_pos] + text[cursor_pos].swapcase() + text[cursor_pos + 1:]
            cursor_pos += 1
            if cursor_pos > len(text) - 1:
                cursor_pos = len(text) - 1
                break

        return sigma.set(text=text, cursor_pos=cursor_pos)

    return sigma


def insert_mode(sigma):
    key = yield sigma

    while True:
        if key == 'escape':
            # the -1 here is simply reflective of how my reference implementation of Vim works (on exiting insert mode,
            # the cursor jumps to the left). Such a behavior makes sense if you see it as exiting append mode, and also
            # has the advantage of guaranteeing to put the cursor in-bounds for normal mode (there is 1 more
            # cursor-position available, at the end, in insert-mode). It has the disadvantage of being asymmetric for
            # 'i'/'escape'.
            return sigma.set(cursor_pos=max(sigma.cursor_pos - 1, 0))

        elif key == 'backspace':
            text, cursor_pos = ibeam_delete(sigma.text, sigma.cursor_pos, sigma.cursor_pos - 1)
            sigma = sigma.set(text=text, cursor_pos=cursor_pos)

        elif key == 'left':
            sigma = sigma.set(cursor_pos=max(sigma.cursor_pos - 1, 0))

        elif key == 'right':
            sigma = sigma.set(cursor_pos=min(sigma.cursor_pos + 1, len(sigma.text)))

        elif len(key) != 1:
            pass  # some special key that we have no behaviors for

        else:
            text, cursor_pos = ibeam_insert(sigma.text, sigma.cursor_pos, key)
            sigma = sigma.set(text=text, cursor_pos=cursor_pos)

        key = yield sigma


def numeral(sigma, key):
    """Parses a 'count' value; returns that count and the first unusable key (to be consumed by some place that _does_
    know what to do with it).

    Note that we don't actually need the state (sigma) to do such parsing, nor do we have anything new to say about that
    state. However, in our current `yield` interface we must _always_ yield the current state if we want to get a key;
    which means we need to know it. A simplification could be: codifying the fact that there is no output information as
    a possible yieldable value (and dealing with it on the receiving end). Because `numeral` is the only example of
    this, I have not yet done that.
    """

    count = 0
    while key.isdigit():
        count *= 10
        count += int(key)
        key = yield sigma

    return key, count


def motion(sigma, key, count):
    """
    >>> from test_utils import Generator
    >>>
    >>> text = 'some text as an example'

    h & l return immediately, no further info required
    >>> g = Generator(motion(Sigma(text, 0), 'l', 5))
    ('R', (5, False, None))

    Findable text
    >>> g = Generator(motion(Sigma(text, 0), 'f', 1))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', (3, True, ('f', 'e')))

    nth occurence using 'count'
    >>> g = Generator(motion(Sigma(text, 0), 'f', 2))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', (6, True, ('f', 'e')))

    Unfindable text returns None
    >>> g = Generator(motion(Sigma(text, 0), 'f', 1))
    ('Y', ('some text as an example', 0))
    >>> g.send('Q')
    ('R', None)

    Not enough occurrences returns None:
    >>> g = Generator(motion(Sigma(text, 0), 'f', 5))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', None)
    """
    if key in ['h', 'left']:
        return max(sigma.cursor_pos - count, 0), False, sigma.last_ft

    if key in ['l', 'right']:
        # In normal mode there are as many positions as characters, hence `len(text) - 1`
        return min(sigma.cursor_pos + count, len(sigma.text) - 1), False, sigma.last_ft

    if key in ['0']:
        return 0, False, sigma.last_ft

    if key in ['$']:
        return len(sigma.text) - 1, True, sigma.last_ft

    if key in [',', ';']:
        if sigma.last_ft is None:
            return None  # repeat last f/t command, but there is None

        last_key, last_char = sigma.last_ft

        if key == ',':
            key = last_key.swapcase()
        else:
            key = last_key

        cursor_pos = sigma.cursor_pos
        for i in range(count):
            result = ftFT(key, last_char, sigma.text, cursor_pos)
            if result is None:
                return result
            cursor_pos, inclusive = result

        return cursor_pos, inclusive, sigma.last_ft

    if key in MOVE_TO_CHAR_KEYS:
        char = yield sigma
        if len(char) != 1:
            return None  # i.e. not actually a char; we cannot jump to special keys

        cursor_pos = sigma.cursor_pos
        for i in range(count):
            result = ftFT(key, char, sigma.text, cursor_pos)
            if result is None:
                return result
            cursor_pos, inclusive = result

        return cursor_pos, inclusive, (key, char)

    return None


def ftFT(key, char, text, cursor_pos):
    """
    >>> s = 'some text as an example'
    >>> check = lambda *args: (ftFT(*args), s[ftFT(*args)[0]])

    From beginning to first 'a'
    >>> check('f', 'a', s, 0)
    ((10, True), 'a')

    From beginning to right before first 'a'
    >>> check('t', 'a', s, 0)
    ((9, True), ' ')

    From first 'a' to next 'a'
    >>> check('f', 'a', s, 10)
    ((13, True), 'a')

    Back to previous 'a'
    >>> check('F', 'a', s, 13)
    ((10, False), 'a')

    Back to right after previous 'a'
    >>> check('T', 'a', s, 13)
    ((11, False), 's')

    Find the last char
    >>> check('f', 'e', s, 20)
    ((22, True), 'e')
    """
    find = text.find if key in ['f', 't'] else text.rfind  # forwards or backwards
    bounds = (cursor_pos + 1, len(text)) if key in ['f', 't'] else (0, cursor_pos)  # first half or second half
    correction = {
        'f': 0,
        'F': 0,
        't': -1,  # 'till
        'T': 1,  # 'till after
    }[key]
    found = find(char, *bounds)

    # TBH, I personally think that the concept of inclusive/exclusive motions is a kludge; an equal amount of
    # expressiveness in a simpler interface can be achieved by simply have a cursor in between characters (i.e. ibeam
    # rather than block) and slightly different choices in the meaning of 'f' and 't' (i.e. to be able to
    # delete-including, 'f' needs to jump to right _after_ the character

    # However, I want the exact same behavior as Vim for this part to lower my own (and other peoples) switching costs,
    # so I'll just reimplement the kludge as well as I understand it)

    # Short example of why 'inclusive' motions are required is the behavior of 'f' and 'F': both of them jump _to_ the
    # indicated character; 'f' puts the ibeam-like cursor that's implicit in the deletion on the right of that
    # character, and 'F' puts it on the left.

    inclusive = key in ['f', 't']

    if found == -1:
        return None

    return found + correction, inclusive


def ibeam_delete(s, i0, i1):
    """
    Returns

    A] a string `s` with the bit between i0 and i1 deleted, treating both indices as 'ibeams', i.e. points in
    between characters, like so:

     0 1 2 3 4 5 6    | string indices
    |a|b|c|d|e|f|g|
    ^ ^ ^ ^ ^ ^ ^ ^
    0 1 2 3 4 5 6 7   | ibeam cursors

    B] The single index i´ representing an ibeam sitting in the now-deleted part.

    Single ibeam represents a no-op:
    >>> ibeam_delete('abcdefg', 5, 5)
    ('abcdefg', 5)

    >>> ibeam_delete('abcdefg', 0, 3)
    ('defg', 0)

    >>> ibeam_delete('abcdefg', 1, 3)
    ('adefg', 1)

    >>> ibeam_delete('abcdefg', 1, 7)
    ('a', 1)

    Order of the cursors does not matter:
    >>> ibeam_delete('abcdefg', 7, 1)
    ('a', 1)

    Bounds are checked (allows for lazy usage of this function; arguably we should raise an error instead)
    >>> ibeam_delete('abcdefg', -1, 99)
    ('', 0)
    """
    lo, hi = tuple(sorted([i0, i1]))
    lo = max(0, lo)
    hi = min(len(s), hi)

    # We need to copy right up to the lo ibeam; right up to the ibeam 'n' means up to and including string-index n-1.
    # Because python slice-notation's RHS excludes its index, this is written as s[0:lo]

    # We need to copy from right after the hi ibeam; right after the ibeam 'n' means from string-index n onwards.
    # Because python slice-notation's LHS includes its index, this is written as s[hi:]

    s = s[0:lo] + s[hi:]
    return s, lo


def ibeam_insert(s, cursor_pos, insertion):
    return s[:cursor_pos] + insertion + s[cursor_pos:], cursor_pos + len(insertion)


def ibeam_slice(s, i0, i1):
    """Returns a slice of between i0 and i1 (either forwards or backwards).
    Bounds are checked (allows for lazy usage of this function; arguably we should raise an error instead)"""

    lo, hi = tuple(sorted([i0, i1]))
    lo = max(0, lo)
    hi = min(len(s), hi)

    return s[lo:hi]


def block_delete(s, i0, i1):
    """
    Returns:

    A] a string `s` with the bit between i0 and i1 deleted, treating both indices as 'block cursors', i.e. indices in a
    string, which are part of the deletion.

    B] The single index i´ representing a block cursor, sitting at the same place Vim would put it:
    * leftmost pre-deletion character
    * but not outside the string
    * unless the string is 0-length, in which case you must put it outside the string (at pos 0)
    (I wish the above definition was simpler; to me it's a hint that "block cursor are a bit funny", but I'm going for
    compatability, not elegance, in this particular part)

    Single block deletes one char:
    >>> block_delete('abcdefg', 5, 5)
    ('abcdeg', 5)

    >>> block_delete('abcdefg', 1, 3)
    ('aefg', 1)

    Order of the cursors does not matter:
    >>> block_delete('abcdefg', 6, 1)
    ('a', 0)

    Bounds are checked (allows for lazy usage of this function; arguably we should raise an error instead)
    >>> block_delete('abcdefg', -1, 99)
    ('', 0)
    """
    lo, hi = tuple(sorted([i0, i1]))
    lo = max(0, lo)
    hi = max(0, min(len(s), hi + 1))

    s = s[0:lo] + s[hi:]
    return s, max(0, min(lo, len(s) - 1))
