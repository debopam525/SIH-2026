"""Mosca 'X + Y > Z' prioritisation.

X = data lifetime (years the data must stay secure)
Y = migration time (years to migrate this asset)
Z = CRQC horizon (a CONFIGURABLE ASSUMPTION, not a prediction)

If X + Y > Z the asset is exposed: a CRQC would arrive before the migration finishes and while
the data still matters. Every result carries an ``assumptions_note`` for the UI to render.
"""
from __future__ import annotations

from dataclasses import dataclass

# Default migration-time estimate (years) by primitive when the asset has no explicit value.
_MIGRATION_TIME_BY_PRIMITIVE = {
    "protocol": 3.0,
    "signature": 3.0,
    "kem": 2.5,
    "key-exchange": 2.5,
    "cipher": 1.5,
    "hash": 1.0,
    "mac": 0.5,
    "kdf": 0.5,
    "unknown": 2.0,
}

_DEFAULT_DATA_LIFETIME_YEARS = 7.0  # conservative mid value when nothing is known


@dataclass
class MoscaResult:
    data_lifetime_years: float
    migration_time_years: float
    crqc_horizon_years: float
    sum_xy: float
    gap_years: float
    exposed: bool
    priority_result: str  # act_now | plan | monitor
    assumptions_note: str


def assess(
    *,
    primitive: str,
    crqc_horizon_years: float,
    data_lifetime_years: float | None = None,
    migration_time_years: float | None = None,
    crqc_note: str = "",
) -> MoscaResult:
    x = float(data_lifetime_years) if data_lifetime_years is not None else _DEFAULT_DATA_LIFETIME_YEARS
    y = (
        float(migration_time_years)
        if migration_time_years is not None
        else _MIGRATION_TIME_BY_PRIMITIVE.get(primitive, _MIGRATION_TIME_BY_PRIMITIVE["unknown"])
    )
    z = float(crqc_horizon_years)
    sum_xy = round(x + y, 2)
    gap = round(sum_xy - z, 2)
    exposed = sum_xy > z

    if gap >= 5:
        priority = "act_now"
    elif exposed or gap >= -3:
        priority = "plan"
    else:
        priority = "monitor"

    x_src = "provided" if data_lifetime_years is not None else f"default {_DEFAULT_DATA_LIFETIME_YEARS}y"
    y_src = "provided" if migration_time_years is not None else f"primitive default for '{primitive}'"
    note = (
        f"ESTIMATE, not a prediction. X (data lifetime) = {x}y [{x_src}]; "
        f"Y (migration time) = {y}y [{y_src}]; Z (CRQC horizon) = {z}y [assumption]. "
        f"X + Y = {sum_xy}y vs Z = {z}y -> gap {gap:+}y. "
        + ("Exposed: begin migration planning now." if exposed
           else "Not currently exposed under these assumptions; re-evaluate if Z shortens.")
    )
    if crqc_note:
        note += " " + crqc_note

    return MoscaResult(
        data_lifetime_years=x,
        migration_time_years=y,
        crqc_horizon_years=z,
        sum_xy=sum_xy,
        gap_years=gap,
        exposed=exposed,
        priority_result=priority,
        assumptions_note=note,
    )
