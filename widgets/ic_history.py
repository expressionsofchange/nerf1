from utils import pmts
from functools import partial

from kivy.clock import Clock
from kivy.core.text import Label
from kivy.graphics import Color, Rectangle
from kivy.metrics import pt
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.widget import Widget

from dsn.history.ic_construct import eich_note_play
from dsn.history.ic_structure import EICHStructure
from dsn.pp.construct import construct_pp_nerd_tree
from dsn.pp.structure import PPSingleLine
from dsn.pp.in_context import (
    construct_iri_top_down,
    InheritedRenderingInformation,
    IriAnnotatedInContextDisplay,
    MULTI_LINE_ALIGNED,
    MULTI_LINE_INDENTED,
)

from dsn.s_expr.score import Score

from spacetime import get_s_address_for_t_address
from s_address import node_for_s_address

from dsn.history.ic_clef import (
    EICHChordCollapse,
    EICHChordExpand,
    EICHCursorMove,
    EICHCursorSet,
)

from widgets.utils import (
    apply_offset,
    BoxNonTerminal,
    BoxTerminal,
    bring_into_offset,
    no_offset,
    OffsetBox,
    X,
    Y,
    flatten_nt_to_dict,
)

from widgets.animate import animate, animate_scalar

from colorscheme import (
    CURIOUS_BLUE,
    GUARDSMAN_RED,
    GREY,
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

from dsn.s_expr.construct import play_note as play_note_regularly
from dsn.s_expr.nerd import NerdSExpr, play_note
from dsn.s_expr.in_context_display import annotated_render_t0, PPAnnotatedInContextDisplay
from dsn.s_expr.in_context_display import ICAtom, ICHAddress, InContextDisplay
from dsn.s_expr.clef import Chord
from dsn.s_expr.clef_address import play_simple_score, score_with_global_address
from dsn.s_expr.simple_score import SimpleScore

ANIMATION_LENGTH = .5  # Seconds

PADDING = PADDING + MARGIN
MARGIN = 0


FOLLOWING = 0
LEADING = 1


def _deepest(note):
    """Finds the 'single leaf of the tree' (our notes have either 1 or 0 children); the exception being 'Chord',
    but as it stands Chords are treated as a single (childless) note themselves and returned."""
    if hasattr(note, 'child_note'):
        return _deepest(note.child_note)  # i.e. for Insert & Extend
    return note  # i.e. everything else, including Chord!


def _x_deepest(note):
    """Searches like _deepest; creates a constructor to rewrap"""
    # Are addresses needed here? probably not (yet?)

    if hasattr(note, 'child_note'):
        # i.e. for Insert & Extend (and their addressed counterparts)... TODO actually: only addressed
        return lambda inner: type(note)(note.address, note.index, _x_deepest(note.child_note)(inner))

    return lambda inner: inner  # i.e. the empty wrapper for everything else, including Chord!


def node_cata(alg, node):
    """A twist on cata: somewhat non-canonical because we pass child_results explicitly as a parameter to alg, rather
    than constructing a new node which has the already transformed values at .children.

    Works for any rose-tree which has its children in .children"""

    node_children = node.children if hasattr(node, 'children') else []

    child_results = [node_cata(alg, child) for child in node_children]
    return alg(node, child_results)


class ICGrouping(InContextDisplay):
    """
    ICGrouping represents: a grouping of InContextDisplay items that has no direct counterpart in an SExpr (and hence:
    is not creating any rendered elements itself but only transparently renders its children)
    """

    def __init__(self, children, address=None):
        pmts(children, list)
        self.children = children
        self.address = address

    def __repr__(self):
        return " ".join(repr(c) for c in self.children)


class HistoryWidget(FocusBehavior, Widget):

    def __init__(self, **kwargs):
        self._invalidated = False

        self.m = kwargs.pop('m')

        # We use tree_widget to peak at its `pp_annotations` attribute in a flagrant violation of data encapsulation.
        # The more thorough solution would be to communicate pp notes over a separate channel; such a solution is left
        # as a todo though.
        self.tree_widget = kwargs.pop('tree_widget')

        self.state_channel = kwargs.pop('state_channel')
        # send-only channel
        self.send_state, _ = self.state_channel.connect(lambda data: None, lambda: None)

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

        self.ds = EICHStructure(Score.empty(), [], 0, [], set())

        self.following_or_leading = FOLLOWING
        self.z_pressed = False
        self.viewport_ds = ViewportStructure(
            ViewportContext(0, 0, 0, 0),
            VRTC(0),
        )
        self.present_viewport_position, self.target_viewport_position = 0, 0

        self.present = {}
        self.animation_time_remaining = 0

        Clock.schedule_interval(self.tick, 1 / 60)
        self.bind(pos=self.invalidate)
        self.bind(size=self.size_change)

    def _best_new_cursor(self, prev_cursor, prev_items, new_items, default):
        """Finds a best new cursor given a previous cursor"""

        searchfor = prev_items[prev_cursor].underlying_node.address.note_address
        for i, item in enumerate(new_items):
            if item.underlying_node.address.note_address == searchfor:
                return i

        return default

    def _items(self, score, t_address, expanded_chords):
        items = []
        for s in reversed(list(score.scores())):
            note_to_render = s.last_note()

            scores = iter(s.scores())
            next(scores)  # the note's own score
            score_up_to_note = next(scores, None)

            if score_up_to_note is None:
                s_expr_before_note = None
            else:
                s_expr_before_note = play_simple_score(score_up_to_note)

            deepest_node = _deepest(note_to_render)

            if isinstance(deepest_node, Chord) and deepest_node.address in expanded_chords:
                items.extend(self._ad_hoc_copy_pasta(s_expr_before_note, note_to_render, t_address, expanded_chords))
                continue

            initial_nerd_s_expr = NerdSExpr.from_s_expr(s_expr_before_note)

            prefix = ICHAddress(_deepest(note_to_render).address, tuple(t_address))

            nerd_s_expr = play_note(note_to_render, initial_nerd_s_expr)

            # we bring the pp-annotations in the address-space of the tree that's actually being displayed by filtering
            # on the the first part of the t-address, and dropping it.
            rewritten_pp_annotations = [
                type(a)(a.score, type(a.annotation)(a.annotation.t_address[len(t_address):]))
                for a in self.tree_widget.ds.pp_annotations
                if a.annotation.t_address[:len(t_address)] == t_address
                ]
            annotated_nerd_s_expr = construct_pp_nerd_tree(nerd_s_expr, rewritten_pp_annotations)

            annotated_renderings = annotated_render_t0(annotated_nerd_s_expr, address=prefix)

            # The return type of the render_* functions is a list of InContextDisplay items; the reasons for there to be
            # more or less than a single return value are:
            # 1. insertions inside deletions (no values returned);
            # 2. set-atom: renders the pre-change and post-change states (multiple values returned)
            # Point 1 does not apply here, because the outermost context is never deleted (true for any context: even
            # though arbitrary nodes may be deleted, that deletion is never part of that node's history, but of its
            # parent's history)
            # Point 2 does apply: we render atom histories when an atom is clicked. To ensure that a single set-atom is
            # rendered as a single item we group the results from render_t0 into a ICGrouping.
            assert len(annotated_renderings) > 0, (
                "An error in the human reasoning in the comment above this line (point 1)")

            if len(annotated_renderings) > 1:
                items.append(PPAnnotatedInContextDisplay(
                    ICGrouping([a.underlying_node for a in annotated_renderings], address=prefix),
                    annotation=PPSingleLine(),  # TBD whether this is correct
                    children=annotated_renderings,
                    ))
            else:
                items.extend(annotated_renderings)

        return items

    def _ad_hoc_copy_pasta(self, s_expr_so_far, chord_containing_node, t_address, expanded_chords):
        # copy_pasta source: _items
        items = []

        chord = _deepest(chord_containing_node)
        rewrap = _x_deepest(chord_containing_node)

        for inner_note in chord.score.notes:
            note_to_render = rewrap(inner_note)

            deepest_node = _deepest(note_to_render)

            if isinstance(deepest_node, Chord) and deepest_node.address in expanded_chords:
                items.extend(self._ad_hoc_copy_pasta(s_expr_so_far, note_to_render, t_address))
                continue

            initial_nerd_s_expr = NerdSExpr.from_s_expr(s_expr_so_far)

            prefix = ICHAddress(_deepest(note_to_render).address, tuple(t_address))

            nerd_s_expr = play_note(note_to_render, initial_nerd_s_expr)

            # we bring the pp-annotations in the address-space of the tree that's actually being displayed by filtering
            # on the the first part of the t-address, and dropping it.
            rewritten_pp_annotations = [
                type(a)(a.score, type(a.annotation)(a.annotation.t_address[len(t_address):]))
                for a in self.tree_widget.ds.pp_annotations
                if a.annotation.t_address[:len(t_address)] == t_address
                ]
            annotated_nerd_s_expr = construct_pp_nerd_tree(nerd_s_expr, rewritten_pp_annotations)

            annotated_renderings = annotated_render_t0(annotated_nerd_s_expr, address=prefix)

            # comment not copied
            assert len(annotated_renderings) > 0, (
                "An error in the human reasoning in the comment above this line (point 1)")

            if len(annotated_renderings) > 1:
                items.append(PPAnnotatedInContextDisplay(
                    ICGrouping([a.underlying_node for a in annotated_renderings], address=prefix),
                    annotation=PPSingleLine(),  # TBD whether this is correct
                    children=annotated_renderings,
                    ))
            else:
                items.extend(annotated_renderings)

            s_expr_so_far = play_note_regularly(note_to_render, s_expr_so_far, SimpleScore)

        return items

    def parent_cursor_update(self, data):
        t_address = data
        local_score = self._local_score(self.ds.score, t_address)
        items = self._items(local_score, t_address, self.ds.expanded_chords)

        self.ds = EICHStructure(
            self.ds.score,
            items,
            self._best_new_cursor(self.ds.cursor, self.ds.items, items, len(local_score) - 1),
            t_address,
            self.ds.expanded_chords,
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

        self.ds = EICHStructure(
            score,
            self._items(local_score, self.ds.tree_t_address, self.ds.expanded_chords),
            self.ds.cursor,
            self.ds.tree_t_address,
            self.ds.expanded_chords,
        )

        self._construct_target_box_structure()

        if len(local_score) > 0:  # guard against "no reasonable cursor, hence no reasonable viewport change"
            # The desirable behavior is: keep the cursor still; Hence: change_source=ELSEWHERE (which matches with the
            # fact that the history-cursor moving is a consequence of cursor move elsewhere)
            self._update_viewport_for_change(change_source=ELSEWHERE)

        self.invalidate()

    def _handle_eich_note(self, eich_note):
        new_cursor, new_expanded_chords, error = eich_note_play(self.ds, eich_note)
        local_score = self._local_score(self.ds.score, self.ds.tree_t_address)

        self.ds = EICHStructure(
            self.ds.score,
            self._items(local_score, self.ds.tree_t_address, new_expanded_chords),
            new_cursor,
            self.ds.tree_t_address,
            new_expanded_chords,
        )

        # TODO: do the below only when in leading mode (but to do so, we need to store the variable local_score as part
        # of our state)
        # Implemented as the quickest way to get this to work; without any regards for performance; It's also yet
        # another piece of evidence that the split over 3 different types of scores is a bad idea. Once we rewrite it,
        # we might instead take the approach of dropping a number of items from the top of the list, in which case the
        # number of items to drop is `len - (new_cursor + 1)`
        score_in_past = Score.from_list(local_score.notes()[:new_cursor + 1])
        self.send_state(score_in_past)

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

        elif textual_code in ['f']:  # f for follow
            self.switch_following_mode()

        elif textual_code in ['up', 'k']:
            self._handle_eich_note(EICHCursorMove(-1))

        elif textual_code in ['down', 'j']:
            self._handle_eich_note(EICHCursorMove(1))

        elif textual_code in ['i']:
            self._handle_eich_note(EICHChordCollapse())

        elif textual_code in ['o']:
            self._handle_eich_note(EICHChordExpand())

        return True

    def size_change(self, *args):
        self._update_viewport_for_change(change_source=ELSEWHERE)
        self.invalidate()

    def invalidate(self, *args):
        self._invalidated = True

    def _get_cursor_dimensions(self):
        # Gets the dimensions (cursor_position, cursor_size, both as scalars). Mirrors the generic version in utils.py
        # implementation: we know that self.target_box_structure is a single NT which contains an NT for each of the
        # "lines" representing notes; we simply look up the relevant line and return its offset and dimensions.
        o, nt = self.target_box_structure.offset_nonterminals[self.ds.cursor]
        return o[Y], nt.outer_dimensions[Y]

    def _update_viewport_for_change(self, change_source):
        # copy-pasta from TreeWidget width changes
        cursor_position, cursor_size = self._get_cursor_dimensions()

        # In the below, all sizes and positions are brought into the positive integers; there is a mirroring `+` in the
        # offset calculation when we actually apply the viewport.
        context = ViewportContext(
            document_size=self.target_box_structure.outer_dimensions[Y] * -1,
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
        offset_nonterminals = self._nts_for_items(self.ds.items)
        root_nt = BoxNonTerminal(offset_nonterminals, [])

        self.target_box_structure = root_nt

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

    def colors_for_properties(self, is_inserted, is_deleted, is_cursor):
        result = {
            (False, False): (GREY, None),
            (False, True):  (GUARDSMAN_RED, None),
            (True, False):  (BLACK, None),
            (True, True):   (CURIOUS_BLUE, None),
        }[is_inserted, is_deleted]

        if is_cursor:
            return WHITE, result[0]
        return result

    def _nts_for_items(self, items):
        result = []
        offset_y = 0

        for i, annotated_rendering in enumerate(items):
            algebra = partial(self._nt_for_iri, i)

            iri_annotated_node = construct_iri_top_down(
                annotated_rendering,

                # We start MULTI_LINE_ALIGNED (but if the first PP node is annotated otherwise the result will reflect
                # that)
                InheritedRenderingInformation(MULTI_LINE_ALIGNED),
                IriAnnotatedInContextDisplay,
            )

            per_step_result = node_cata(algebra, iri_annotated_node)

            result.append(OffsetBox((0, offset_y), per_step_result))

            INTER_ITEM_MARGIN = 20
            offset_y += per_step_result.outer_dimensions[Y] - INTER_ITEM_MARGIN

        return result

    def _nt_for_iri(self, index_in_items, iri_annotated_node, children_nts):
        pmts(iri_annotated_node, IriAnnotatedInContextDisplay)

        is_cursor = index_in_items == self.ds.cursor
        if iri_annotated_node.annotation.multiline_mode == MULTI_LINE_ALIGNED:
            f = self._nt_for_node_as_multi_line_aligned
        elif iri_annotated_node.annotation.multiline_mode == MULTI_LINE_INDENTED:
            f = self._nt_for_node_as_multi_line_indented
        else:  # SINGLE_LINE
            f = self._nt_for_node_single_line

        return f(iri_annotated_node, children_nts, is_cursor)

    def _nt_for_node_single_line(self, iri_annotated_node, children_nts, is_cursor):
        pmts(iri_annotated_node, IriAnnotatedInContextDisplay)
        node = iri_annotated_node.underlying_node

        if isinstance(node, ICGrouping):
            offset_nonterminals = []
            offset_right = 0

            for nt in children_nts:
                offset_nonterminals.append(OffsetBox((offset_right, 0), nt))
                offset_right += nt.outer_dimensions[X]

            return BoxNonTerminal(offset_nonterminals, [])

        if isinstance(node, ICAtom):
            return BoxNonTerminal([], [no_offset(
                self._t_for_text(
                    node.atom,
                    self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
                    node.address))])

        t = self._t_for_text(
            "(",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("open-paren")
            )

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for nt in children_nts:
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(
            ")",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("close-paren")
            )
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _nt_for_node_as_multi_line_aligned(self, iri_annotated_node, children_nts, is_cursor):
        # "Align with index=1, like so:..  (xxx yyy
        #                                       zzz)

        pmts(iri_annotated_node, IriAnnotatedInContextDisplay)
        node = iri_annotated_node.underlying_node

        if isinstance(node, ICGrouping):
            offset_nonterminals = []
            offset_right = 0

            for nt in children_nts:
                offset_nonterminals.append(OffsetBox((offset_right, 0), nt))
                offset_right += nt.outer_dimensions[X]

            return BoxNonTerminal(offset_nonterminals, [])

        if isinstance(node, ICAtom):
            return BoxNonTerminal([], [no_offset(self._t_for_text(
                node.atom,
                self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
                node.address))])

        t = self._t_for_text(
            "(",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("open-paren")
            )
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(children_nts) > 0:
            nt = children_nts[0]

            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), nt)
            )
            offset_right += nt.outer_dimensions[X]

            if len(children_nts) > 1:
                for nt in children_nts[1:]:
                    offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
                    offset_down += nt.outer_dimensions[Y]

                # get the final drawn item to figure out where to put the closing ")"
                last_drawn = nt.get_all_terminals()[-1]
                offset_right += last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

                # go "one line" back up
                offset_down -= last_drawn.item.outer_dimensions[Y]

        else:
            offset_right = t.outer_dimensions[X]

        t = self._t_for_text(
            ")",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("close-paren"))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _nt_for_node_as_multi_line_indented(self, iri_annotated_node, children_nts, is_cursor):
        # "Indented with the equivalent of 2 spaces, like so:..  (xxx yyy
        #                                                           zzz)
        # TODO this is a pure copy/pasta with _nt_for_node_as_multi_line_aligned with alterations; factoring the
        # commonalities out would be the proper course of action here.

        pmts(iri_annotated_node, IriAnnotatedInContextDisplay)
        node = iri_annotated_node.underlying_node

        if isinstance(node, ICGrouping):
            offset_nonterminals = []
            offset_right = 0

            for nt in children_nts:
                offset_nonterminals.append(OffsetBox((offset_right, 0), nt))
                offset_right += nt.outer_dimensions[X]

            return BoxNonTerminal(offset_nonterminals, [])

        if isinstance(node, ICAtom):
            return BoxNonTerminal([], [no_offset(self._t_for_text(
                node.atom,
                self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
                node.address))])

        if len(node.children) <= 2:
            return self._nt_for_node_single_line(iri_annotated_node, children_nts, is_cursor)

        t = self._t_for_text(
            "(",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("open-paren")
            )

        offset_right_i0 = t.outer_dimensions[X]
        offset_right_i2_plus = t.outer_dimensions[X] * 1.3  # ")  " by approximation
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        nt = children_nts[0]
        offset_nonterminals.append(OffsetBox((offset_right_i0, offset_down), nt))
        offset_right_i1 = offset_right_i0 + nt.outer_dimensions[X]

        nt = children_nts[1]
        offset_nonterminals.append(OffsetBox((offset_right_i1, offset_down), nt))
        offset_down += nt.outer_dimensions[Y]

        for nt in children_nts[2:]:
            offset_nonterminals.append(OffsetBox((offset_right_i2_plus, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        # get the final drawn item to figure out where to put the closing ")"
        last_drawn = nt.get_all_terminals()[-1]
        offset_right = offset_right_i2_plus + last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

        # go "one line" back up
        offset_down -= last_drawn.item.outer_dimensions[Y]

        t = self._t_for_text(
            ")",
            self.colors_for_properties(node.is_inserted, node.is_deleted, is_cursor),
            node.address.with_render("close-paren"))
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

        if fg is None:
            instructions += []
        else:
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

    def from_point(self, point):
        # Given a point, determine what was clicked; Mirrors the generic version in utils.py. Differences:
        # * we simply iterate over the top-level items only.
        # * y-based only (we don't check x coordinates at all)

        for i, (o, nt) in enumerate(self.target_box_structure.offset_nonterminals):
            if o[Y] >= point[Y] >= o[Y] + nt.outer_dimensions[Y]:  # '>=' rather than '<=': kivy's origin is bottom-left
                return i

        return None

    def on_touch_down(self, touch):
        # COPY/PASTE FROM tree.py, with some adaptions

        ret = super(HistoryWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        self.focus = True

        clicked_item = self.from_point(bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._handle_eich_note(EICHCursorSet(clicked_item))

        return True

    def switch_following_mode(self):
        self.following_or_leading = FOLLOWING if self.following_or_leading is LEADING else LEADING
        self.switch_editor_panes(self.following_or_leading)
