from type_factories import nout_factory

from dsn.s_expr.clef import Note

NoteNout, NoteCapo, NoteSlur, NoteNoutHash = nout_factory(Note, "Note")
