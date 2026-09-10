from app.analysis import quantum


def test_rsa_is_quantum_vulnerable_with_explanation():
    v = quantum.assess(algorithm="RSA", algorithm_family="public-key", key_size="2048")
    assert v.status == "quantum-vulnerable"
    assert v.shor_impact == "broken"
    assert "Shor" in v.explanation
    assert v.harvest_now_decrypt_later is True


def test_aes256_is_quantum_safe_via_context_rule():
    v = quantum.assess(algorithm="AES", algorithm_family="symmetric", key_size="256", mode="GCM")
    assert v.status == "quantum-safe"
    assert "128-bit" in v.explanation or "Grover" in v.explanation


def test_aes128_is_weakened_not_broken():
    v = quantum.assess(algorithm="AES", algorithm_family="symmetric", key_size="128", mode="CBC")
    assert v.status == "quantum-weakened"
    assert v.grover_impact == "sqrt_speedup"


def test_aes_ecb_flagged_broken_by_mode_not_name():
    v = quantum.assess(algorithm="AES", algorithm_family="symmetric", key_size="256", mode="ECB")
    assert v.status == "broken-classical"
    assert any("ECB" in n for n in v.context_notes)


def test_md5_broken_classical_regardless_of_quantum():
    v = quantum.assess(algorithm="MD5", algorithm_family="broken-hash")
    assert v.status == "broken-classical"


def test_mlkem_is_quantum_safe():
    v = quantum.assess(algorithm="ML-KEM", algorithm_family="pqc-kem", primitive="kem")
    assert v.status == "quantum-safe"


def test_unknown_algorithm_returns_unknown_with_explanation():
    v = quantum.assess(algorithm="Frobnicate-9000", algorithm_family="unknown")
    assert v.status == "unknown"
    assert v.explanation


def test_legacy_tls_version_is_broken():
    v = quantum.assess(algorithm="TLS", algorithm_family="protocol", version="TLSv1")
    assert v.status == "broken-classical"


def test_tls13_still_quantum_vulnerable_key_exchange():
    v = quantum.assess(algorithm="TLS", algorithm_family="protocol", version="TLSv1.3")
    assert v.status == "quantum-vulnerable"
