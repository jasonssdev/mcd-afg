"""Typed vocabulary of the thesis: decisions, relations, meetings, participants, questions.

This package has no I/O and no dependency on the corpus, the instrument, or any
condition. Everything here is a pure data model (pydantic v2) plus the small amount of
pure logic that follows directly from a definition in thesis section 5 (e.g.
``TemporalRelation.inverted()``).
"""
