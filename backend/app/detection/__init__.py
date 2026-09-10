"""Detection layer: rules -> (AST-ready) -> (ML-ready), then normalization to CryptographicAsset.

All detectors implement :class:`app.detection.rules.Detector`. Adding a tree-sitter or ML
backend means adding a class here and registering it in ``DETECTORS`` — no scanner or engine
code changes.
"""
