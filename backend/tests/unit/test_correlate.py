from app.cbom.correlate import correlate
from app.detection.rules import RawFinding


def _rf(algo, fam, prim, scanner, path, line=1, conf="confirmed_api", lib="unknown", **extra):
    rf = RawFinding(algorithm=algo, family=fam, primitive=prim, confidence=conf,
                    matched_indicator=f"{algo} hit", signature_id=f"sig-{algo}",
                    detector=scanner, location=path, line=line, library=lib)
    rf.extra.update({"scanner": scanner, "component": extra.get("component", path.split("/")[0])})
    return rf


def test_same_identity_same_component_merges_into_one_asset():
    findings = [
        _rf("AES", "symmetric", "cipher", "source", "svc/a.py", line=10),
        _rf("AES", "symmetric", "cipher", "source", "svc/b.py", line=20),
    ]
    assets = correlate(findings)
    aes = [a for a in assets if a.algorithm == "AES"]
    assert len(aes) == 1
    assert len(aes[0].evidence) == 2


def test_different_components_stay_separate():
    findings = [
        _rf("AES", "symmetric", "cipher", "source", "svcA/a.py", component="svcA"),
        _rf("AES", "symmetric", "cipher", "source", "svcB/b.py", component="svcB"),
    ]
    assert len({a.dedup_key for a in correlate(findings)}) == 2


def test_highest_confidence_wins():
    findings = [
        _rf("MD5", "hash", "hash", "binary", "bin/x.so", conf="weak_textual"),
        _rf("MD5", "hash", "hash", "source", "bin/x.py", conf="confirmed_api", component="bin"),
    ]
    # different components -> two assets; check each keeps its own confidence
    assets = {a.dedup_key: a for a in correlate(findings)}
    confs = {a.detection_confidence for a in assets.values()}
    assert "confirmed_api" in confs


def test_source_and_dependency_for_same_library_do_not_double_count():
    src = _rf("RSA", "public-key", "signature", "source", "svc/keys.py", lib="cryptography",
              component="svc")
    dep = _rf("RSA", "public-key", "signature", "dependency", "requirements.txt",
              lib="cryptography")
    dep.extra["component"] = "cryptography"
    assets = correlate([src, dep])
    rsa = [a for a in assets if a.algorithm == "RSA"]
    assert len(rsa) == 1
    assert set(rsa[0].sources) == {"source", "dependency"}
    assert len(rsa[0].evidence) == 2
