"""AMI Meeting Corpus ingestion: download, low-level NXT parsing, layer discovery,
paso-cero inventory, participant/native-language derivation, and transcript rendering.

Nothing in this package is run automatically. ``download.py`` fetches the corpus only when
explicitly invoked (``afg corpus download``); every other module degrades gracefully, or
raises :class:`afg.corpus.inventory.CorpusNotDownloadedError`, when the corpus is absent.
"""
