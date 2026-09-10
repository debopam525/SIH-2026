from app.analysis import quantum
from app.analysis.risk import FACTORS, AppContext, score


def _q(algo, fam, **kw):
    return quantum.assess(algorithm=algo, algorithm_family=fam, **kw)


def test_all_nine_factors_present_and_1_to_5():
    r = score(primitive="signature", algorithm_family="public-key",
              quantum=_q("RSA", "public-key", key_size="2048"), app=None)
    assert set(r.factors) == set(FACTORS)
    for f in r.factors.values():
        assert 1 <= f["value"] <= 5
        assert f["source"] in ("derived", "application", "default")
        assert f["rationale"]


def test_score_is_reproducible():
    args = {
        "primitive": "kem",
        "algorithm_family": "public-key",
        "quantum": _q("RSA", "public-key", key_size="2048"),
        "app": AppContext(name="x", business_criticality=5, data_sensitivity=5,
                          data_lifetime_years=30, system_lifetime_years=15),
    }
    a = score(**args)
    b = score(**args)
    assert a.weighted_score == b.weighted_score
    assert a.risk_category == b.risk_category
    assert a.factors == b.factors


def test_sensitive_long_lived_rsa_is_critical_or_high():
    r = score(primitive="signature", algorithm_family="public-key",
              quantum=_q("RSA", "public-key", key_size="1024"),
              app=AppContext(name="pay", business_criticality=5, data_sensitivity=5,
                             data_lifetime_years=30, system_lifetime_years=20))
    assert r.risk_category in ("critical", "high")
    assert "CRITICAL" in r.explanation or "HIGH" in r.explanation


def test_quantum_safe_symmetric_is_low_or_medium():
    r = score(primitive="cipher", algorithm_family="symmetric",
              quantum=_q("AES", "symmetric", key_size="256", mode="GCM"),
              app=AppContext(name="x", business_criticality=2, data_sensitivity=2,
                             data_lifetime_years=2, system_lifetime_years=3))
    assert r.risk_category in ("low", "medium")


def test_missing_app_metadata_marked_as_default_source():
    r = score(primitive="hash", algorithm_family="hash",
              quantum=_q("SHA-256", "hash"), app=None)
    assert any(f["source"] == "default" for f in r.factors.values())
    assert "neutral default" in r.explanation


def test_custom_weights_change_score():
    q = _q("RSA", "public-key", key_size="2048")
    base = score(primitive="signature", algorithm_family="public-key", quantum=q, app=None)
    tilted = score(primitive="signature", algorithm_family="public-key", quantum=q, app=None,
                   weights={k: (0.9 if k == "quantum_vulnerability" else 0.0125) for k in FACTORS})
    assert tilted.weighted_score != base.weighted_score
