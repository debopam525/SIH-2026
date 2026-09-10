from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import _mosca_dict, _rec_dict, _risk_dict, asset_to_out
from app.cbom.export import to_cyclonedx
from app.core.runtime_settings import get_crqc_horizon, get_crqc_note, get_risk_weights
from app.models.asset import CryptographicAsset
from app.models.scan import Scan

REPORT_TYPES = [
    "inventory", "algorithms", "vulnerability", "exposure", "recommendations",
    "migration_roadmap", "executive_summary", "full",
]
_RISK_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _assets(db: Session, scan_id: str) -> list[CryptographicAsset]:
    return list(
        db.scalars(
            select(CryptographicAsset)
            .where(CryptographicAsset.scan_id == scan_id)
            .options(
                selectinload(CryptographicAsset.risk),
                selectinload(CryptographicAsset.mosca),
                selectinload(CryptographicAsset.recommendation),
                selectinload(CryptographicAsset.evidence),
                selectinload(CryptographicAsset.application),
            )
        ).all()
    )


def build_report(db: Session, rtype: str, scan_id: str) -> dict:
    scan = db.get(Scan, scan_id)
    assets = _assets(db, scan_id)
    outs = [asset_to_out(a) for a in assets]
    meta = {
        "report_type": rtype,
        "scan_id": scan_id,
        "target": scan.target if scan else "unknown",
        "generated_at": datetime.now(UTC).isoformat(),
        "asset_count": len(assets),
        "tool": "ECDAT 0.1.0",
    }

    def inv() -> dict:
        return {"assets": [o.model_dump() for o in outs]}

    def algorithms() -> dict:
        by_algo: dict[str, dict] = {}
        for a in assets:
            k = f"{a.algorithm}|{a.key_size}|{a.mode}|{a.version}"
            e = by_algo.setdefault(k, {
                "algorithm": a.algorithm, "family": a.algorithm_family, "primitive": a.primitive,
                "key_size": a.key_size, "mode": a.mode, "version": a.version,
                "protocol": a.protocol, "occurrences": 0, "libraries": set(), "locations": [],
            })
            e["occurrences"] += 1
            if a.library_dependency and a.library_dependency != "unknown":
                e["libraries"].add(a.library_dependency)
            e["locations"].append(a.usage_location)
        rows = []
        for e in by_algo.values():
            e["libraries"] = sorted(e["libraries"])
            e["locations"] = e["locations"][:25]
            rows.append(e)
        rows.sort(key=lambda r: r["occurrences"], reverse=True)
        return {"algorithms": rows}

    def vulnerability() -> dict:
        rows = []
        for a in assets:
            d = asset_to_out(a).model_dump()
            d["risk"] = _risk_dict(a)
            d["mosca"] = _mosca_dict(a)
            rows.append(d)
        rows.sort(key=lambda d: (_RISK_ORDER.get(d.get("risk_category") or "", 0),
                                 d.get("weighted_score") or 0), reverse=True)
        return {
            "weights_in_effect": get_risk_weights(db),
            "crqc_horizon_years": get_crqc_horizon(db),
            "crqc_note": get_crqc_note(db),
            "assets": rows,
        }

    def exposure() -> dict:
        apps: dict[str, dict] = {}
        for a in assets:
            name = a.application.name if a.application else "(unassigned)"
            e = apps.setdefault(name, {
                "application": name,
                "owner": a.application.owner if a.application else None,
                "business_unit": a.application.business_unit if a.application else None,
                "business_criticality": a.application.business_criticality if a.application else None,
                "data_sensitivity": a.application.data_sensitivity if a.application else None,
                "data_lifetime_years": a.application.data_lifetime_years if a.application else None,
                "assets": 0, "critical": 0, "high": 0, "medium": 0, "low": 0,
                "harvest_now_decrypt_later": 0,
            })
            e["assets"] += 1
            if a.risk:
                e[a.risk.risk_category] = e.get(a.risk.risk_category, 0) + 1
            if a.mosca and a.mosca.exposed:
                e["harvest_now_decrypt_later"] += 1
        rows = sorted(apps.values(),
                      key=lambda r: (r["critical"], r["high"], r["assets"]), reverse=True)
        return {"applications": rows}

    def recommendations() -> dict:
        rows = []
        for a in assets:
            if not a.recommendation:
                continue
            d = _rec_dict(a)
            d.update({"asset_id": a.asset_id, "asset_name": a.asset_name,
                      "current_key_size": a.key_size, "family": a.algorithm_family})
            rows.append(d)
        rows.sort(key=lambda d: _RISK_ORDER.get(d["migration_priority"], 0), reverse=True)
        return {"recommendations": rows}

    def migration_roadmap() -> dict:
        buckets: dict[str, list] = {"critical": [], "high": [], "medium": [], "low": []}
        for a in assets:
            prio = a.recommendation.migration_priority if a.recommendation else "low"
            buckets.setdefault(prio, []).append({
                "asset_id": a.asset_id,
                "asset_name": a.asset_name,
                "application": a.application.name if a.application else None,
                "current": a.algorithm,
                "target": a.recommendation.candidate_algorithm if a.recommendation else None,
                "type": a.recommendation.recommendation_type if a.recommendation else None,
                "status": a.migration.status if a.migration else "not_started",
                "readiness": a.migration.readiness if a.migration else 0,
                "mosca_gap_years": a.mosca.gap_years if a.mosca else None,
            })
        wave = 1
        waves = []
        for prio in ("critical", "high", "medium", "low"):
            if buckets[prio]:
                waves.append({"wave": wave, "priority": prio, "items": buckets[prio],
                              "count": len(buckets[prio])})
                wave += 1
        return {"waves": waves}

    def executive_summary() -> dict:
        risk_counts = dict.fromkeys(("critical", "high", "medium", "low"), 0)
        q_counts: dict[str, int] = {}
        for o in outs:
            if o.risk_category:
                risk_counts[o.risk_category] += 1
            q_counts[o.quantum_status] = q_counts.get(o.quantum_status, 0) + 1
        vulnerable = q_counts.get("quantum-vulnerable", 0) + q_counts.get("broken-classical", 0)
        already_pqc = sum(1 for o in outs if o.algorithm_family in ("pqc-kem", "pqc-signature"))
        top = sorted(outs, key=lambda o: (_RISK_ORDER.get(o.risk_category or "", 0),
                                          o.weighted_score or 0), reverse=True)[:10]
        headline = (
            f"{len(outs)} cryptographic assets discovered; {vulnerable} are quantum-vulnerable "
            f"or already broken, {risk_counts['critical']} rated CRITICAL. "
            f"{already_pqc} assets already use post-quantum algorithms."
        )
        return {
            "headline": headline,
            "totals": {"assets": len(outs), "vulnerable": vulnerable, "already_pqc": already_pqc},
            "risk_distribution": risk_counts,
            "quantum_distribution": q_counts,
            "crqc_assumption": {"horizon_years": get_crqc_horizon(db), "note": get_crqc_note(db)},
            "top_priorities": [o.model_dump() for o in top],
            "disclaimer": "Mosca timing and quantum-horizon figures are configurable estimates, "
                          "not predictions.",
        }

    builders = {
        "inventory": inv,
        "algorithms": algorithms,
        "vulnerability": vulnerability,
        "exposure": exposure,
        "recommendations": recommendations,
        "migration_roadmap": migration_roadmap,
        "executive_summary": executive_summary,
    }
    if rtype == "full":
        data = {name: fn() for name, fn in builders.items()}
        data["cbom"] = to_cyclonedx(db, scan_id)
    else:
        data = builders[rtype]()
    return {"meta": meta, "data": data}


# --------------------------------------------------------------------------- renderers
def render_json(report: dict) -> bytes:
    return json.dumps(report, indent=2, default=str).encode("utf-8")


def render_csv(report: dict) -> bytes:
    rtype = report["meta"]["report_type"]
    data = report["data"]
    buf = io.StringIO()
    rows: list[dict] = []
    if rtype == "full":
        rows = [{"section": k, "json": json.dumps(v, default=str)} for k, v in data.items()]
    elif "assets" in data:
        rows = [_flatten(r) for r in data["assets"]]
    else:
        key = next(iter(data))
        val = data[key]
        rows = [_flatten(r) for r in val] if isinstance(val, list) else [_flatten(data)]
    if not rows:
        rows = [{"note": "no rows"}]
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _flatten(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, default=str)[:2000]
        else:
            out[k] = v
    return out


def render_html(report: dict) -> bytes:
    meta = report["meta"]
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<style>body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:2rem;color:#1e293b}"
        "h1{font-size:22px}h2{font-size:17px;margin-top:2rem;border-bottom:1px solid #cbd5e1;padding-bottom:.3rem}"
        "table{border-collapse:collapse;width:100%;margin:.5rem 0}th,td{border:1px solid #cbd5e1;padding:6px 8px;text-align:left;font-size:12px}"
        "th{background:#f1f5f9}code{background:#f1f5f9;padding:1px 4px;border-radius:3px}"
        ".crit{color:#b91c1c;font-weight:600}.high{color:#c2410c;font-weight:600}</style>",
        f"<h1>ECDAT {escape(meta['report_type'].replace('_', ' ').title())} Report</h1>",
        f"<p>Target: <code>{escape(str(meta['target']))}</code> &middot; Scan "
        f"<code>{escape(meta['scan_id'])}</code> &middot; Generated {escape(meta['generated_at'])} "
        f"&middot; {meta['asset_count']} assets</p>",
    ]
    _html_walk(report["data"], parts, level=2)
    parts.append(
        "<hr><p style='color:#64748b;font-size:11px'>Mosca timing and quantum-horizon values are "
        "configurable estimates, not predictions.</p>"
    )
    return "".join(parts).encode("utf-8")


def _html_walk(node, parts: list[str], level: int) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                parts.append(f"<h{level}>{escape(str(k))} ({len(v)})</h{level}>")
                parts.append(_html_table(v))
            elif isinstance(v, (dict, list)):
                parts.append(f"<h{level}>{escape(str(k))}</h{level}>")
                _html_walk(v, parts, min(level + 1, 4))
            else:
                parts.append(f"<p><b>{escape(str(k))}:</b> {escape(str(v))}</p>")
    elif isinstance(node, list):
        parts.append(_html_table([x if isinstance(x, dict) else {"value": x} for x in node]))


def _html_table(rows: list[dict]) -> str:
    cols: list[str] = []
    for r in rows[:200]:
        for k in r:
            if k not in cols and not isinstance(r[k], (dict, list)):
                cols.append(k)
    cols = cols[:12]
    head = "".join(f"<th>{escape(c)}</th>" for c in cols)
    body = []
    for r in rows[:200]:
        tds = []
        for c in cols:
            val = escape(str(r.get(c, "")))
            cls = ""
            if c in ("risk_category", "migration_priority") and val in ("critical", "high"):
                cls = f" class='{ 'crit' if val == 'critical' else 'high' }'"
            tds.append(f"<td{cls}>{val}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><tr>{head}</tr>{''.join(body)}</table>"


def render_pdf(report: dict) -> tuple[bytes, str]:
    """Return (bytes, actual_format). Falls back to HTML if weasyprint is unavailable."""
    html = render_html(report)
    try:
        from weasyprint import HTML  # type: ignore

        return HTML(string=html.decode("utf-8")).write_pdf(), "pdf"
    except Exception:  # noqa: BLE001  (ImportError or native lib missing)
        return html, "html"
