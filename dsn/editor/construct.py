"""
Tools to "play notes for the editor clef", which may be thought of as "executing editor commands".
"""

from s_address import node_for_s_address, s_dfs

from dsn.s_expr.utils import (
    bubble_history_up,
    insert_text_at,
    insert_node_at,
    replace_text_at,
)

from dsn.s_expr.clef import Delete, Insert, Extend

from dsn.s_expr.structure import List

from dsn.editor.clef import (
    CursorChild,
    CursorDFS,
    CursorParent,
    CursorSet,
    EDelete,
    EncloseWithParent,
    InsertNodeChild,
    InsertNodeSibbling,
    MoveSelectionChild,
    MoveSelectionSibbling,
    LeaveChildrenBehind,
    SwapSibbling,
    TextInsert,
    TextReplace,
)


def edit_note_play(structure, edit_note):
    # :: EditStructure, EditNote => (new) s_cursor, score, error

    # NOTES about score: implemented as a (not going back to the beginning of time) python-list of notes.

    def an_error():
        return structure.s_cursor, [], True

    if isinstance(edit_note, TextInsert):
        note = insert_text_at(structure.tree, edit_note.parent_s_address, edit_note.index, edit_note.text)
        new_s_cursor = edit_note.parent_s_address + [edit_note.index]
        return new_s_cursor, [note], False

    if isinstance(edit_note, TextReplace):
        note = replace_text_at(structure.tree, edit_note.s_address, edit_note.text)
        return edit_note.s_address, [note], False

    if isinstance(edit_note, InsertNodeSibbling):
        if structure.s_cursor == []:
            return an_error()  # adding sibblings to the root is not possible (it would lead to a forest)

        # There is no need to check that the new index is a valid one. (Assuming: the cursor is valid, and direction is
        # in the range [0, 1]; such assumptions fit with the general idea of "we only check that the user's command can
        # be executed at this point, we do not check for arbitrary programming errors here). The proof flows directly
        # from the idea that, for lists of length n, insertions at [0, n] are valid (insertion at n being an append).
        index = structure.s_cursor[-1] + edit_note.direction

        note = insert_node_at(structure.tree, structure.s_cursor[:-1], index)
        new_s_cursor = structure.s_cursor[:-1] + [index]

        return new_s_cursor, [note], False

    if isinstance(edit_note, InsertNodeChild):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not isinstance(cursor_node, List):
            # for now... we just silently ignore the user's request when they ask to add a child node to a non-node
            return an_error()

        index = len(cursor_node.children)
        note = insert_node_at(structure.tree, structure.s_cursor, index)
        new_s_cursor = structure.s_cursor + [index]

        return new_s_cursor, [note], False

    if isinstance(edit_note, EDelete):
        if structure.s_cursor == []:
            # silently ignored ('delete root' is not defined, because the root is assumed to exist.)
            return an_error()

        delete_from = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]

        note = Delete(delete_at_index)

        if delete_at_index == len(node_for_s_address(structure.tree, delete_from).children) - 1:
            # deletion makes cursor pos invalid: up to parent (alternative: sibbling-up first, until no more sibblings)
            new_s_cursor = delete_from
        else:
            new_s_cursor = structure.s_cursor  # "stay in place (although new contents slide into the cursor position)

        note = bubble_history_up(note, structure.tree, delete_from)

        return new_s_cursor, [note], False

    if isinstance(edit_note, SwapSibbling):
        if structure.s_cursor == []:
            return an_error()  # root has no sibblings

        parent = node_for_s_address(structure.tree, structure.s_cursor[:-1])
        index = structure.s_cursor[-1] + edit_note.direction

        if not (0 <= index <= len(parent.children) - 1):
            return an_error()

        # For now, SwapSibbling is simply implemented as a "delete and insert"; if (or when) we'll introduce "Move" into
        # the Clef, we should note the move here.
        # It is also a prime candidate for Chords!

        parent_s_address = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]

        reinsert_later_node = node_for_s_address(structure.tree, structure.s_cursor)

        delete_note = Delete(delete_at_index)
        score = [bubble_history_up(delete_note, structure.tree, parent_s_address)]

        for i, note in enumerate(reinsert_later_node.score.notes()):
            type_ = Insert if i == 0 else Extend
            reinsertion = type_(index, note)

            score.append(bubble_history_up(reinsertion, structure.tree, parent_s_address))

        new_cursor = structure.s_cursor[:-1] + [index]
        return new_cursor, score, False

    if isinstance(edit_note, MoveSelectionChild):
        raise Exception("NotImplemented")
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)

        if not hasattr(cursor_node, 'children'):
            return an_error()  # The target must be a node to be able to add as a child

        return do_move(structure, edit_note, structure.s_cursor, len(cursor_node.children))

    if isinstance(edit_note, MoveSelectionSibbling):
        raise Exception("NotImplemented")
        if len(structure.s_cursor) == 0:
            return an_error()  # there is no sibbling of the root node

        # edit_note.direction points to a valid insertion point for the same reasons detailed in the comment on
        # InsertNodeSibbling
        return do_move(structure, edit_note, structure.s_cursor[:-1], structure.s_cursor[-1] + edit_note.direction)

    if isinstance(edit_note, LeaveChildrenBehind):
        raise Exception("NotImplemented")
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not hasattr(cursor_node, 'children'):
            return an_error()  # Leave _children_ behind presupposes the existance of children

        if structure.s_cursor == []:
            return an_error()  # Root cannot die

        # For now, LeaveChildrenBehind is simply implemented as a "delete and insert"; if (or when) we'll introduce
        # "Move" into the Clef, we should note the move here.

        parent_s_address = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]
        delete_from_hash = node_for_s_address(structure.tree, parent_s_address).metadata.nout_hash

        p, hash_ = calc_possibility(NoteSlur(Delete(delete_at_index), delete_from_hash))
        posacts = [p]

        removed_node = node_for_s_address(structure.tree, structure.s_cursor)
        for i, child in enumerate(removed_node.children):
            p, hash_ = calc_possibility(NoteSlur(Insert(structure.s_cursor[-1] + i, child.metadata.nout_hash), hash_))
            posacts.append(p)

        # In general, leaving the cursor at the same s_address will be great: post-deletion you'll be in the right spot
        new_cursor = structure.s_cursor
        if len(removed_node.children) == 0:
            # ... however, if there are no children to leave behind... this "right spot" may be illegal
            parent_node = node_for_s_address(structure.tree, parent_s_address)
            if len(parent_node.children) == 1:
                # if the deleted node was the only node: fall back to the parent
                new_cursor = parent_s_address
            else:
                # otherwise, make sure to stay in bounds.
                new_cursor[len(new_cursor) - 1] = min(
                    len(parent_node.children) - 1 - 1,  # len - 1 idiom; -1 for deletion.
                    new_cursor[len(new_cursor) - 1])

        posacts += bubble_history_up(hash_, structure.tree, parent_s_address)

        return new_cursor, posacts, False

    if isinstance(edit_note, EncloseWithParent):
        raise Exception("NotImplemented")
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)

        if structure.s_cursor == []:
            # I am not sure about this one yet: should we have the option to create a new root? I don't see any direct
            # objections (by which I mean: it's possible in terms of the math), but I still have a sense that it may
            # create some asymmetries. For now I'm disallowing it; we'll see whether a use case arises.
            return an_error()

        # For now, EncloseWithParent is simply implemented as a "replace with the parent"; if (or when) we'll introduce
        # "Move" (in particular: the MoveReplace) into the Clef, we should note the move here.

        parent_s_address = structure.s_cursor[:-1]
        replace_at_index = structure.s_cursor[-1]
        replace_on_hash = node_for_s_address(structure.tree, parent_s_address).metadata.nout_hash

        reinsert_later_hash = node_for_s_address(structure.tree, structure.s_cursor).metadata.nout_hash

        p_capo, hash_capo = calc_possibility(NoteCapo())
        p_create, hash_create = calc_possibility(NoteSlur(BecomeNode(), hash_capo))

        p_enclosure, hash_enclosure = calc_possibility(NoteSlur(Insert(0, reinsert_later_hash), hash_create))

        p_replace, hash_replace = calc_possibility(
            NoteSlur(Replace(replace_at_index, hash_enclosure), replace_on_hash))

        posacts = [p_capo, p_create, p_enclosure, p_replace] + bubble_history_up(
            hash_replace, structure.tree, parent_s_address)

        # We jump the cursor to the newly enclosed location:
        new_cursor = structure.s_cursor + [0]

        return new_cursor, posacts, False

    def move_cursor(new_cursor):
        return new_cursor, [], False

    if isinstance(edit_note, CursorDFS):
        dfs = s_dfs(structure.tree, [])
        dfs_index = dfs.index(structure.s_cursor) + edit_note.direction
        if not (0 <= dfs_index <= len(dfs) - 1):
            return an_error()
        return move_cursor(dfs[dfs_index])

    """At some point I had "regular sibbling" (as opposed to DFS sibbling) in the edit_clef. It looks like this:

        if structure.s_cursor == []:
            return an_error()  # root has no sibblings

        parent = node_for_s_address(structure.tree, s_cursor[:-1])
        index = s_cursor[-1] + edit_node.direction

        if not (0 <= index <= len(parent.children) - 1):
            return an_error()
        return move_cursor(s_cursor[:-1] + [index])
    """
    if isinstance(edit_note, CursorSet):
        return move_cursor(edit_note.s_address)

    if isinstance(edit_note, CursorParent):
        if structure.s_cursor == []:
            return an_error()
        return move_cursor(structure.s_cursor[:-1])

    if isinstance(edit_note, CursorChild):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not hasattr(cursor_node, 'children') or len(cursor_node.children) == 0:
            return an_error()
        return move_cursor(structure.s_cursor + [0])

    raise Exception("Unknown Note")


def do_move(structure, edit_note, target_parent_path, target_index):
    selection_edge_0 = edit_note.selection_edge_0
    selection_edge_1 = edit_note.selection_edge_1

    def an_error():
        return structure.s_cursor, [], True

    if selection_edge_0[:-1] != selection_edge_1[:-1]:
        # i.e. if not same-parent: this is an error. This may very well be too restrictive, but I'd rather move in the
        # direction of "relax constraints later" than in the other directions. One particular reason I'm so restrictive
        # for now: if I ever want to express a note "move" using a target_node, a source node and to indices in the
        # source node, such a single-parent restriction is indeed a necessity.

        # Note that "single parent" implies "same depth", but not vice versa. One possible relaxation is: make the
        # restriction on "same depth" instead.

        # Generally, the paths towards relaxation are to either [a] "be smart about the meaning of the selection's
        # edges", i.e. find the first common ancestor and the relevant children of that ancestor or [b] to not care so
        # much about single-parent.

        return an_error()

    if selection_edge_0 <= (target_parent_path + [target_index])[:len(selection_edge_0)] <= selection_edge_1:
        # If the full target location, truncated to the length of the sources, is (inclusively) in the source's range,
        # you're trying to move to [a descendant of] yourself. This is illegal. Moving something to a child of itself:
        # I simply don't know what it would mean. Moving something to the same location (single source item, target path
        # identical to the source path) could at least be understood to mean the no-op, so it's slightly less
        # meaningless, but here I don't find that enough, so I'm just calling both scenarios error-scenarios.

        # This implies protection against moving the root node around (because everything descends from the root node)
        return an_error()

    source_parent_path = selection_edge_0[:-1]
    source_parent = node_for_s_address(structure.tree, source_parent_path)

    target_parent = node_for_s_address(structure.tree, target_parent_path)

    # For now, the "edit move" operations are simply implemented as a "insert and delete"; if (or when) we'll introduce
    # "Move" into the Clef, we should note the move here.

    posacts = []

    source_index_lo, source_index_hi = sorted([selection_edge_0[-1], selection_edge_1[-1]])

    hash_ = target_parent.metadata.nout_hash

    for target_offset, source_index in enumerate(range(source_index_lo, source_index_hi + 1)):  # edge-inclusive range
        insert_hash = node_for_s_address(structure.tree, source_parent_path + [source_index]).metadata.nout_hash
        p, hash_ = calc_possibility(NoteSlur(Insert(target_index + target_offset, insert_hash), hash_))

        posacts.append(p)

    weave_correction = 0
    cursor_correction = 0

    # TODO this part is still broken:

    # Not only if the parents are exactly the same, but also if one parent is a prefix of the other (said differently:
    # the longest_common_prefix of both parents matches one of them).

    # In that case, we need to somehow connect the parents....

    # (For the case of "parents match exactly", I did this using the idea "just don't reset hash_"... which works,
    # because it allows you to continue operating on the the same "future". But in the case of shared prefix, this won't
    # work.
    if source_parent_path != target_parent_path:
        wdr_hash = hash_
        hash_ = source_parent.metadata.nout_hash

    else:
        if target_index < source_index_lo:
            # We insert before we delete. If we do this on the same parent, and the insertions happen at lower indices
            # than the deletions, they will affect the locations where the deletions must take place, by precisely the
            # number of insertions that happened. (If we reverse the order of operations, we have the opposite problem)

            # The reason we have this problem at all, is because we implement something that is atomic from the user's
            # point of view in a non-atomic way in the clef. The problem may auto-disappear if we add "Move" to the
            # clef.

            # Another way we could handle the problem is once we have some tools to "realinearize while preserving
            # meaning". I.e. we have deletions, we have insertions: at one point (e.g. once we build the cooperative
            # editor) we should be able to express "weave those together, rewriting indices as required".

            # In the if-statement above, we could pick either lo/hi for the comparison; source_index_lo and
            # source_index_hi will never straddle target_index, because of the child-of-yourself checks at the top.

            weave_correction = source_index_hi - source_index_lo + 1
        else:
            cursor_correction = source_index_hi - source_index_lo + 1

        # we do _not_ fetch hash_ here, the idea being: it's the hash we just created.
        # nor do we bubble up (yet); we can do a single bubble-up

    for source_index in range(source_index_lo, source_index_hi + 1):  # edge-inclusive range
        # Note: we just Delete n times at the "lo" index (everything shifting to the left after each deletion)
        p, hash_ = calc_possibility(NoteSlur(Delete(source_index_lo + weave_correction), hash_))
        posacts.append(p)

    if source_parent_path != target_parent_path:
        posacts = posacts + weave_disjoint_replaces(
            structure.tree,
            target_parent_path, wdr_hash,
            source_parent_path, hash_)

    else:
        posacts = posacts + bubble_history_up(hash_, structure.tree, source_parent_path)

    # The current solution for "where to put the cursor after the move" is "at the end". This "seems intuitive" (but
    # that may just be habituation). In any case, it's wat e.g. LibreOffice does when cut/pasting. (However, for a
    # mouse-drag initiated move in LibreOffice, the selection is preserved).

    # As it stands: the selection disappears automatically, because it points at a no-longer existing location.  If we
    # want to make the selection appear at the target-location, we need to change the interface of edit_note_play to
    # include the resulting selection.

    new_cursor = target_parent_path + [target_index + target_offset - cursor_correction]

    return new_cursor, posacts, False
