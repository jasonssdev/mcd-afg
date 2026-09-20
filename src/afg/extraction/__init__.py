"""OE2: automatic extraction of decisions and their temporal relations (thesis section 3).

``protocol.py`` defines the extractor interface; ``openkos_adapter.py`` implements it over
the OpenKOS instrument (thesis section 5.9); ``runner.py`` implements the repeated-run
variance reporting required by thesis section 5.8, generically over any
:class:`~afg.extraction.protocol.Extractor`.
"""
