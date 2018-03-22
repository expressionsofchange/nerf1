class SelectionNote(object):
    pass


class AttachDetach(SelectionNote):
    pass


class SwitchToOtherEnd(SelectionNote):
    pass


class ClearSelection(SelectionNote):
    pass


class SelectionContextChange(SelectionNote):
    """The Selection lives in the context of an editor's structure. In other words: "EditorStructureChange" correponds
    to a SelectionContextChange.

    As a more general note on connecting various related structures, the following: The idea of "ContextChange" (here
    and for scrollview) is an instance of "update the secondary structure using a signal 'the main structure has
    changed'", as opposed to exposing the primary _clef_ to the secondary clef, i.e. exposing the notes the other score.
    This has pros & cons: pro is that you don't actually need to understand the clef; con is that you cannot see the
    actually played notes and (potentially) optimize for that.

    For the case of "Selection", it's more or less why we created a separate clef & structure for that in the first
    place. Namely the idea that cursor-updates in the editor may happen in various ways, and that for the selection the
    effect on the is always the same.
    """

    def __init__(self, context):
        self.context = context
