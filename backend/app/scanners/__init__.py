"""Discovery scanners. Each implements :class:`app.scanners.base.Scanner` and returns
``RawFinding`` objects; the runner correlates + persists them. Scanners never raise on a single
bad file — they collect per-file errors into the result.
"""
