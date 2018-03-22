"""
The dsn 'viewports' implements some tools for managing a viewport on a document.

The main design challenge is: coming up with a model that behaves in a predictable and useful manner in a distributed
environment (multiple sources of change to the underlying document). In other words: what if you're editing a document,
but someone else is editing the same document but in another location, e.g. above the place that you're editing? In such
a situation, you want the viewport to remain focussed on the part of the document that you're looking at.

Another similar question is: what if you're dragging on a scrollbar (which expresses a position in the document,
somewhere between 0 and 100%) and someone else is removing large parts of  the document while you're dragging? The
question then becomes: should such removals affect the position of the scrollbar, or should the position of the
scrollbar remain constant and a different part of the document be shown? The answer is: the latter, because the user is
in the process of dragging, that should take preference.

An underlying question is: how can we combine different such models of scrolling? The answer is: we have a modal
approach; each input into the scrolling mechanism changes the mode to be associated with that last input. Example: if
you scroll to 50%, and provide no further input, the viewport will be at 50%. If the document is then changed, the
viewport will remain at 50% (which is then at a different place in the document).

All cursor-movements and edit operations put the viewport in a cursor-related mode (showing the viewport relative to the
cursor). Any changes to the document from the outside will keep the cursor where it is on the screen, changing the
document around it.
"""
