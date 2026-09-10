"""NEGATIVE / downgrade cases: crypto tokens that must NOT become confirmed assets."""

# We should migrate RSA and ECDSA to PQC next quarter.  <-- prose, no API call: no finding
DOC = "Historically this module used AES and 3DES for payloads."  # string literal: no finding

# cipher = algorithms.AES(key)   <-- commented-out real call: detected but DOWNGRADED confidence


def parse(data):
    # nothing cryptographic happens here
    return data.strip().lower()
