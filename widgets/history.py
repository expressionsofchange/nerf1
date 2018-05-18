from utils import pmts

from kivy.clock import Clock
from kivy.core.text import Label
from kivy.graphics import Color, Rectangle
from kivy.metrics import pt
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.widget import Widget

from dsn.history.construct import eh_note_play
from dsn.history.structure import EHStructure

from dsn.s_expr.score import Score
from dsn.s_expr.construct import play_score
from dsn.s_expr.structure import Atom, List

from spacetime import get_s_address_for_t_address
from s_address import node_for_s_address

from dsn.history.clef import (
    EHCursorSet,
    EHCursorChild,
    EHCursorDFS,
    EHCursorParent,
)

from widgets.utils import (
    annotate_boxes_with_s_addresses,
    apply_offset,
    BoxNonTerminal,
    BoxTerminal,
    bring_into_offset,
    cursor_dimensions,
    from_point,
    no_offset,
    OffsetBox,
    X,
    Y,
)
from colorscheme import (
    BLACK,
    WHITE,
)
from widgets.layout_constants import (
    get_font_size,
    MARGIN,
    PADDING,
)

from dsn.viewports.structure import ViewportStructure, VRTC, ViewportContext
from dsn.viewports.construct import play_viewport_note
from dsn.viewports.clef import (
    ViewportContextChange,
    MoveViewportRelativeToCursor,
    CURSOR_TO_BOTTOM,
    CURSOR_TO_CENTER,
    CURSOR_TO_TOP,
    VIEWPORT_LINE_DOWN,
    VIEWPORT_LINE_UP,
)


class HistoryWidget(FocusBehavior, Widget):

    def __init__(self, **kwargs):
        self._invalidated = False

        self.m = kwargs.pop('m')

        # Not the best name ever, but at least it clearly indicates we're talking about the channel which contains
        # information on "data" changes (as opposed to "cursor" changes)
        self.data_channel = None

        super(HistoryWidget, self).__init__(**kwargs)

        # In __init__ we don't have any information available yet on our state. Which means we cannot draw ourselves.
        # This gets fixed the moment we get some data from e.g. our parent. In practice this happens before we get to
        # refresh from e.g. the size/pos bindings, but I'd like to make that flow a bit more explicit.
        #
        # AFAIU:
        # 1. We could basically set any value below.

        self.ds = EHStructure(Score.empty(), List([]), [0], [])

        self.z_pressed = False
        self.viewport_ds = ViewportStructure(
            ViewportContext(0, 0, 0, 0),
            VRTC(0),
        )

        self.bind(pos=self.invalidate)
        self.bind(size=self.invalidate)

    def parent_cursor_update(self, data):
        t_address = data

        local_score = self._local_score(self.ds.score, t_address)
        self.ds = EHStructure(
            self.ds.score,
            List([n.to_s_expression() for n in local_score.notes()]),
            [0],  # If we're bound to a different s_cursor in the parent tree, we unconditionally reset our own cursor
            t_address,
        )
        self._construct_box_structure()
        # The desirable behavior is: follow the cursor; Hence: user_moved_cursor=True (even though the history-cursor
        # moving is only a consequence of cursor move elsewhere)
        self._update_viewport_for_change(user_moved_cursor=True)
        self.invalidate()

    def receive_from_parent(self, data):
        pmts(data, Score)
        self.update_score(data)

    def _local_score(self, score, tree_t_address):
        tree = play_score(self.m, score)
        s_address = get_s_address_for_t_address(tree, tree_t_address)

        if s_address is None:
            # because changes to the Score and the Cursor are not communicated to us in a transactional way, deletions
            # in the tree will lead to a (temporarily) invalid cursor. We set our own score to the empty one in that
            # case; the cursor_update that follows right after will restore the situation
            return Score.empty()

        cursor_node = node_for_s_address(tree, s_address)
        return cursor_node.score

    def update_score(self, score):
        # For each "tree cursor" change, we reset our own cursor to the end (most recent item)
        # (because the final item may actually contain subitems, this does not necessarily put the viewport at the
        # lowest possible position; this is something to be aware of because it might cause some confusion). At some
        # point this may be automatically solved, e.g. if we change the behavior of cursor-following to be "follow the
        # cursor, making sure it is in-view including the recursive subparts).
        local_score = self._local_score(score, self.ds.tree_t_address)
        s_cursor = [len(local_score) - 1]

        self.ds = EHStructure(
            score,
            List([n.to_s_expression() for n in local_score.notes()]),
            s_cursor,
            self.ds.tree_t_address,
        )

        self._construct_box_structure()

        if len(local_score) > 0:  # guard against "no reasonable cursor, hence no reasonable viewport change"
            # If nout_hash update results in a cursor-reset, the desirable behavior is: follow the cursor; if the cursor
            # remains the same, the value of user_moved_cursor doesn't matter. Hence: user_moved_cursor=True
            self._update_viewport_for_change(user_moved_cursor=True)

        self.invalidate()

    def _handle_eh_note(self, eh_note):
        new_s_cursor, error = eh_note_play(self.ds, eh_note)

        self.ds = EHStructure(
            self.ds.score,
            List([n.to_s_expression() for n in self.ds.score.notes()]),
            new_s_cursor,
        )

        self._construct_box_structure()
        self._update_viewport_for_change(user_moved_cursor=True)
        self.invalidate()

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        FocusBehavior.keyboard_on_key_down(self, window, keycode, text, modifiers)

        code, textual_code = keycode

        if modifiers == ['ctrl'] and textual_code in ['e', 'y']:
            # For now, these are the only ctrl-key keys we handle; once we get more of those, they should get a better
            # home.
            note = MoveViewportRelativeToCursor({'e': VIEWPORT_LINE_UP, 'y': VIEWPORT_LINE_DOWN}[textual_code])
            self.viewport_ds = play_viewport_note(note, self.viewport_ds)
            self.invalidate()

        elif self.z_pressed:
            self.z_pressed = False
            if textual_code in ['z', 'b', 't']:
                lookup = {
                    'z': CURSOR_TO_CENTER,
                    'b': CURSOR_TO_BOTTOM,
                    't': CURSOR_TO_TOP,
                }
                note = MoveViewportRelativeToCursor(lookup[textual_code])
                self.viewport_ds = play_viewport_note(note, self.viewport_ds)
                self.invalidate()

        elif textual_code in ['z']:
            self.z_pressed = True

        elif textual_code in ['left', 'h']:
            self._handle_eh_note(EHCursorParent())

        elif textual_code in ['right', 'l']:
            self._handle_eh_note(EHCursorChild())

        elif textual_code in ['up', 'k']:
            self._handle_eh_note(EHCursorDFS(-1))

        elif textual_code in ['down', 'j']:
            self._handle_eh_note(EHCursorDFS(1))

        return True

    def invalidate(self, *args):
        if not self._invalidated:
            Clock.schedule_once(self.refresh, -1)
            self._invalidated = True

    def _update_viewport_for_change(self, user_moved_cursor):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        cursor_position, cursor_size = cursor_dimensions(self.box_structure, self.ds.s_cursor)

        # In the below, all sizes and positions are brought into the positive integers; there is a mirroring `+` in the
        # offset calculation when we actually apply the viewport.
        context = ViewportContext(
            document_size=self.box_structure.underlying_node.outer_dimensions[Y] * -1,
            viewport_size=self.size[Y],
            cursor_size=cursor_size * -1,
            cursor_position=cursor_position * -1)

        note = ViewportContextChange(
            context=context,
            user_moved_cursor=user_moved_cursor,
        )
        self.viewport_ds = play_viewport_note(note, self.viewport_ds)

    def _construct_box_structure(self):
        offset_nonterminals = self._nts()
        self.box_structure = annotate_boxes_with_s_addresses(BoxNonTerminal(offset_nonterminals, []), [])

    def refresh(self, *args):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y] + self.viewport_ds.get_position())

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self._render_box(self.box_structure.underlying_node)

        self._invalidated = False

    def colors_for_cursor(self, is_cursor):
        if is_cursor:
            return WHITE, BLACK

        return BLACK, WHITE

    def _nts(self):
        result = []
        offset_y = 0

        for i, node in enumerate(self.ds.node.children):
            per_step_result = self._nt_for_node(node, i)
            result.append(OffsetBox((0, offset_y), per_step_result))

            offset_y += per_step_result.outer_dimensions[Y]

        return result

    def _nt_for_node(self, node, x):
        # NOTE about how this was stolen in broad lines from the tree's rendering mechanism.
        return self.bottom_up_construct(self._nt_for_node_single_line, node, [x])

    def bottom_up_construct(self, f, node, s_address):
        node_children = node.children if hasattr(node, 'children') else []
        children = [self.bottom_up_construct(f, child, s_address + [i]) for i, child in enumerate(node_children)]
        return f(node, children, s_address)

    def _nt_for_node_single_line(self, node, children_nts, s_address):
        is_cursor = s_address == self.ds.s_cursor

        if isinstance(node, Atom):
            return BoxNonTerminal([], [no_offset(
                self._t_for_text(node.atom, self.colors_for_cursor(is_cursor)))])

        t = self._t_for_text("(", self.colors_for_cursor(is_cursor))
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for nt in children_nts:
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", self.colors_for_cursor(is_cursor))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _render_box(self, box):
        # Pure copy/pasta.
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    # ## Section for drawing boxes
    def _t_for_text(self, text, colors):
        # Copy/pasta from tree.py
        fg, bg = colors
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - PADDING - MARGIN - content_height - MARGIN - PADDING)
        bottom_right = (bottom_left[X] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[Y])

        instructions = [
            Color(*bg),
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                ),
            Color(*fg),
            Rectangle(
                pos=(bottom_left[0] + PADDING + MARGIN, bottom_left[1] + PADDING + MARGIN),
                size=text_texture.size,
                texture=text_texture,
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

    def _texture_for_text(self, text):
        if text in self.m.texture_for_text:
            return self.m.texture_for_text[text]

        kw = {
            'font_size': pt(get_font_size()),
            # 'font_name': 'Oxygen',
            'bold': False,
            'anchor_x': 'left',
            'anchor_y': 'top',
            'padding_x': 0,
            'padding_y': 0,
            'padding': (0, 0)}

        # While researching max_width I ran into the following potential solution: add the below 3 parameters to the
        # `kw`.  In the end I didn't choose it, because I wanted something even simpler (and without '...' dots)
        # 'text_size': (some_width, None),
        # 'shorten': True,
        # 'shorten_from': 'right',

        label = Label(text=text, **kw)
        label.refresh()

        self.m.texture_for_text[text] = label.texture
        return label.texture

    def on_touch_down(self, touch):
        # COPY/PASTE FROM tree.py, with some

        ret = super(HistoryWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        self.focus = True

        clicked_item = from_point(self.box_structure, bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._handle_eh_note(EHCursorSet(clicked_item.annotation))

        return True
