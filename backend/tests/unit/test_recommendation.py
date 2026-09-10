from app.analysis import quantum
from app.analysis.recommendation import recommend


def _q(algo, fam, **kw):
    return quantum.assess(algorithm=algo, algorithm_family=fam, **kw)


def test_rsa_keyexchange_maps_to_mlkem():
    r = recommend(algorithm="RSA", algorithm_family="public-key", primitive="key-exchange",
                  quantum=_q("RSA", "public-key", key_size="2048"))
    assert r.use_case == "kem"
    assert "ML-KEM" in r.top.name or "MLKEM" in r.top.name
    assert r.alternatives
    assert r.rationale
    assert all("w=" in r.rationale for _ in [0])  # factors listed


def test_ecdsa_maps_to_signature_scheme():
    r = recommend(algorithm="ECDSA", algorithm_family="elliptic-curve", primitive="signature",
                  quantum=_q("ECDSA", "elliptic-curve"))
    assert r.use_case == "signature"
    assert any(s in r.top.name for s in ("ML-DSA", "SLH-DSA", "Falcon", "ECDSA"))


def test_aes128_gets_symmetric_upgrade_not_pqc():
    r = recommend(algorithm="AES", algorithm_family="symmetric", primitive="cipher",
                  quantum=_q("AES", "symmetric", key_size="128", mode="CBC"))
    assert r.recommendation_type in ("symmetric_upgrade", "config_change")
    assert "256" in r.top.name


def test_already_pqc_recommends_no_change():
    r = recommend(algorithm="ML-KEM", algorithm_family="pqc-kem", primitive="kem",
                  quantum=_q("ML-KEM", "pqc-kem", primitive="kem"))
    assert r.recommendation_type == "no_change"
    assert r.migration_priority == "low"


def test_broken_primitive_urgency_in_rationale():
    r = recommend(algorithm="MD5", algorithm_family="broken-hash", primitive="hash",
                  quantum=_q("MD5", "broken-hash"), risk_category="high", mosca_priority="act_now")
    assert "broken" in r.rationale.lower()
    assert r.migration_priority in ("critical", "high")


def test_top_and_alternatives_show_factor_scores():
    r = recommend(algorithm="RSA", algorithm_family="public-key", primitive="signature",
                  quantum=_q("RSA", "public-key", key_size="2048"))
    assert set(r.top.factor_scores) >= {"security_level", "compatibility", "migration_cost"}
    for alt in r.alternatives:
        assert alt.factor_scores
        assert alt.score >= 0
