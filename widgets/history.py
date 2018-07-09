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
# from dsn.s_expr.construct import play_score
from dsn.s_expr.structure import Atom, List
from dsn.s_expr.clef_address import play_simple_score, score_with_global_address, InScore
from dsn.s_expr.simple_score import SimpleScore

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
    flatten_nt_to_dict,
)

from widgets.animate import animate, animate_scalar

from colorscheme import (
    BLACK,
    WHITE,
)
from widgets.layout_constants import (
    get_font_size,
    PADDING,
    MARGIN,
)

from dsn.viewports.structure import ViewportStructure, VRTC, ViewportContext
from dsn.viewports.construct import play_viewport_note
from dsn.viewports.clef import (
    ViewportContextChange,
    MoveViewportRelativeToCursor,
    CURSOR_TO_BOTTOM,
    CURSOR_TO_CENTER,
    CURSOR_TO_TOP,
    ELSEWHERE,
    HERE,
    VIEWPORT_LINE_DOWN,
    VIEWPORT_LINE_UP,
)

ANIMATION_LENGTH = .5  # Seconds


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

        self.ds = EHStructure(Score.empty(), List([], address=()), [0], [])

        self.z_pressed = False
        self.viewport_ds = ViewportStructure(
            ViewportContext(0, 0, 0, 0),
            VRTC(0),
        )
        self.present_viewport_position, target_viewport_position = 0, 0

        self.present = {}
        self.animation_time_remaining = 0

        Clock.schedule_interval(self.tick, 1 / 60)
        self.bind(pos=self.invalidate)
        self.bind(size=self.size_change)

    def _best_new_cursor(self, prev_s_cursor, prev_node, new_node, default):
        """Finds a best new cursor given a previous cursor"""
        # Note: I find all this mapping between various address schemes rather ad hoc, but it works.

        def _best(s_expr_node, global_address, path_so_far):
            """Find the best match for global_address in s_expr_node;
            Return an s_address to this (which is collected in a variable path_so_far)"""

            if global_address == s_expr_node.address:
                return path_so_far  # precise match, return

            for i, child in enumerate(getattr(s_expr_node, 'children', [])):
                if len(global_address) > len(s_expr_node.address):
                    # This branch is here to deal with descending into chords' list field. The hackyness of it arises
                    # from the fact that the global note-address that we're looking for encodes the fact that a note is
                    # InScore somewhere, but the list-expr that is used to represent that score does itself not have an
                    # address which is InScore. Hence, the general descend-by-prefix-matching trick from below doesn't
                    # work. In a picture:

                    # if you're looking for something inside a chord:
                    # (chord (....OVER-HERE... ))
                    # that something will have an address like (3, @1), and will be marked as such.
                    # but on the way you'll encounter a list, with address (3, 'list'), which _is_ the right thing to
                    # descend into.

                    # The key here is the if-statement below: if the_next part of the global address to consider is an
                    # InScore, and the child we're currently considering is the list-field of the score, you're on
                    # track: descend. The if-statement above (comparing the lenghts) is only here to ensure there
                    # actually is a next part of the global address to consider (i.e. guard against index out of bounds)

                    # Determining the next part to consider: one beyond the end of s_expr_node.address.
                    the_next = global_address[len(s_expr_node.address) - 1 + 1]
                    if isinstance(the_next, InScore) and child.address[-1] == 'list':
                        return _best(child, global_address, path_so_far + [i])  # it's better

                if child.address == global_address[:len(child.address)]:
                    return _best(child, global_address, path_so_far + [i])  # it's better

            return path_so_far  # no child is better; return yourself

        prev_selected_node = node_for_s_address(prev_node, prev_s_cursor)
        global_address = prev_selected_node.address

        result = _best(new_node, global_address, [])
        if result == []:
            return default

        return result

    def parent_cursor_update(self, data):
        t_address = data

        local_score = self._local_score(self.ds.score, t_address)
        as_s_expr = List([n.to_s_expression() for n in local_score.notes()], address=())

        self.ds = EHStructure(
            self.ds.score,
            as_s_expr,
            self._best_new_cursor(self.ds.s_cursor, self.ds.node, as_s_expr, [len(local_score) - 1]),
            t_address,
        )
        self._construct_target_box_structure()

        # The desirable behavior is: keep the cursor still; Hence: change_source=ELSEWHERE (which matches with the fact
        # that the history-cursor moving is a consequence of cursor move elsewhere)
        self._update_viewport_for_change(change_source=ELSEWHERE)
        self.invalidate()

    def receive_from_parent(self, data):
        pmts(data, Score)
        self.update_score(data)

    def _local_score(self, score, tree_t_address):
        annotated_score = score_with_global_address(score)

        tree = play_simple_score(annotated_score)
        s_address = get_s_address_for_t_address(tree, tree_t_address)

        if s_address is None:
            # because changes to the Score and the Cursor are not communicated to us in a transactional way, deletions
            # in the tree will lead to a (temporarily) invalid cursor. We set our own score to the empty one in that
            # case; the cursor_update that follows right after will restore the situation
            return SimpleScore.empty()

        cursor_node = node_for_s_address(tree, s_address)

        return cursor_node.score

    def update_score(self, score):
        local_score = self._local_score(score, self.ds.tree_t_address)

        self.ds = EHStructure(
            score,
            List([n.to_s_expression() for n in local_score.notes()], address=()),
            self.ds.s_cursor,
            self.ds.tree_t_address,
        )

        self._construct_target_box_structure()

        # The desirable behavior is: keep the cursor still; Hence: change_source=ELSEWHERE (which matches with the fact
        # that the history-cursor moving is a consequence of cursor move elsewhere)
        self._update_viewport_for_change(change_source=ELSEWHERE)

        self.invalidate()

    def _handle_eh_note(self, eh_note):
        new_s_cursor, error = eh_note_play(self.ds, eh_note)
        local_score = self._local_score(self.ds.score, self.ds.tree_t_address)

        self.ds = EHStructure(
            self.ds.score,
            List([n.to_s_expression() for n in local_score.notes()], address=()),
            new_s_cursor,
            self.ds.tree_t_address,
        )

        self._construct_target_box_structure()
        self._update_viewport_for_change(change_source=HERE)
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

    def size_change(self, *args):
        self._update_viewport_for_change(change_source=ELSEWHERE)
        self.invalidate()

    def invalidate(self, *args):
        self._invalidated = True

    def _update_viewport_for_change(self, change_source):
        # As it stands: copy-pasta from TreeWidget width changes
        cursor_position, cursor_size = cursor_dimensions(self.target_box_structure, self.ds.s_cursor)

        # In the below, all sizes and positions are brought into the positive integers; there is a mirroring `+` in the
        # offset calculation when we actually apply the viewport.
        context = ViewportContext(
            document_size=self.target_box_structure.underlying_node.outer_dimensions[Y] * -1,
            viewport_size=self.size[Y],
            cursor_size=cursor_size * -1,
            cursor_position=cursor_position * -1)

        note = ViewportContextChange(
            context=context,
            change_source=change_source,
        )
        self.viewport_ds = play_viewport_note(note, self.viewport_ds)

        self.target_viewport_position = self.viewport_ds.get_position()
        self.animation_time_remaining = ANIMATION_LENGTH

    def _construct_target_box_structure(self):
        offset_nonterminals = self._nts(self.ds.node)
        root_nt = BoxNonTerminal(offset_nonterminals, [])

        self.target_box_structure = annotate_boxes_with_s_addresses(root_nt, [])

        self.target = flatten_nt_to_dict(root_nt, (0, 0))
        self.animation_time_remaining = ANIMATION_LENGTH

    def tick(self, dt):
        if self.animation_time_remaining > 0:
            self.present = animate(dt / self.animation_time_remaining, self.present, self.target)
            self.present_viewport_position = animate_scalar(
                dt / self.animation_time_remaining, self.present_viewport_position, self.target_viewport_position)

            self.animation_time_remaining = self.animation_time_remaining - dt
            self._invalidated = True

        if not self._invalidated:  # either b/c animation, or explicitly
            return

        # Actually draw
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y] + self.present_viewport_position)

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self._render_box(BoxNonTerminal([], list(self.present.values())))

        self._invalidated = False

    def colors_for_cursor(self, is_cursor):
        if is_cursor:
            return WHITE, BLACK

        return BLACK, None

    def _nts(self, s_expr_node):
        result = []
        offset_y = 0

        for i, node in enumerate(s_expr_node.children):
            per_step_result = self.bottom_up_construct(self._nt_for_node_single_line, node, [i])

            result.append(OffsetBox((0, offset_y), per_step_result))

            offset_y += per_step_result.outer_dimensions[Y]

        return result

    def bottom_up_construct(self, alg, node, s_address):
        # combines the idea of a catamorphism (with explicit passing of child_results, rather than the more canonical
        # approach which reconstructs nodes with child_results) with the the passing of the s_address in the tree for
        # each visited node.

        node_children = node.children if hasattr(node, 'children') else []
        child_results = [self.bottom_up_construct(alg, child, s_address + [i]) for i, child in enumerate(node_children)]
        return alg(node, child_results, s_address)

    def _nt_for_node_single_line(self, node, children_nts, s_address):
        is_cursor = s_address == self.ds.s_cursor

        if isinstance(node, Atom):
            return BoxNonTerminal([], [no_offset(
                self._t_for_text(node.atom, self.colors_for_cursor(is_cursor), node.address))])

        t = self._t_for_text("(", self.colors_for_cursor(is_cursor), node.address + ("open-paren",))
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for nt in children_nts:
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", self.colors_for_cursor(is_cursor), node.address + ("close-paren",))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _render_box(self, box):
        # Pure copy/pasta.
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    # This is rather ad hoc (a.k.a. hackish) but I cannot find a more proper way to do it in Kivy.
                    # i.e. there is no PushMatrix / Translate equivalent for alpha-blending.
                    if isinstance(instruction, Color):
                        self.canvas.add(Color(instruction.r, instruction.g, instruction.b, o.alpha))
                    else:
                        self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    # ## Section for drawing boxes
    def _t_for_text(self, text, colors, address):
        # Copy/pasta from tree.py (w/ addressing)
        fg, bg = colors
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - MARGIN - PADDING - content_height - PADDING - MARGIN)
        bottom_right = (bottom_left[X] + MARGIN + PADDING + content_width + PADDING + MARGIN, bottom_left[Y])

        if bg is None:
            instructions = []
        else:
            instructions = [
                Color(*bg),
                Rectangle(
                    pos=(bottom_left[0] + MARGIN, bottom_left[1] + MARGIN),
                    size=(content_width + 2 * PADDING, content_height + 2 * PADDING),
                    ),
            ]

        instructions += [
            Color(*fg),
            Rectangle(
                pos=(bottom_left[0] + MARGIN + PADDING, bottom_left[1] + MARGIN + PADDING),
                size=text_texture.size,
                texture=text_texture,
                ),
        ]

        return BoxTerminal(instructions, bottom_right, address)

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

        # TODO click-while-animating
        clicked_item = from_point(self.target_box_structure, bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._handle_eh_note(EHCursorSet(clicked_item.annotation))

        return True
