from app.analysis.mosca import assess


def test_long_data_lifetime_triggers_exposure():
    r = assess(primitive="signature", crqc_horizon_years=15, data_lifetime_years=25)
    assert r.exposed is True
    assert r.sum_xy > r.crqc_horizon_years
    assert r.priority_result in ("act_now", "plan")
    assert "ESTIMATE" in r.assumptions_note


def test_short_lifetime_not_exposed():
    r = assess(primitive="hash", crqc_horizon_years=15, data_lifetime_years=1,
               migration_time_years=0.5)
    assert r.exposed is False
    assert r.priority_result in ("monitor", "plan")


def test_assumptions_exposed_for_ui():
    r = assess(primitive="kem", crqc_horizon_years=10)
    assert r.crqc_horizon_years == 10
    assert r.migration_time_years > 0  # primitive default applied
    assert "X + Y" in r.assumptions_note
    assert "not a prediction" in r.assumptions_note


def test_gap_math_is_exact():
    r = assess(primitive="cipher", crqc_horizon_years=12, data_lifetime_years=10,
               migration_time_years=5)
    assert r.sum_xy == 15
    assert r.gap_years == 3
    assert r.exposed is True


def test_crqc_horizon_shortening_increases_priority():
    long_h = assess(primitive="signature", crqc_horizon_years=30, data_lifetime_years=10)
    short_h = assess(primitive="signature", crqc_horizon_years=5, data_lifetime_years=10)
    order = {"monitor": 0, "plan": 1, "act_now": 2}
    assert order[short_h.priority_result] >= order[long_h.priority_result]
