from app.detection.normalization import normalize
from app.detection.rules import RuleDetector, language_for, run_detectors

RD = RuleDetector()


def test_language_detection():
    assert language_for("a/b/c.py") == "python"
    assert language_for("x.js") == "javascript"
    assert language_for("sshd_config") == "config"
    assert language_for("nginx.conf") == "config"


def test_rsa_keygen_detected_as_confirmed_api():
    code = "from cryptography.hazmat.primitives.asymmetric import rsa\n" \
           "k = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n"
    findings = RD.detect(code, "svc/keys.py", "python")
    rsa_f = [f for f in findings if f.algorithm == "RSA"]
    assert rsa_f
    assert rsa_f[0].confidence == "confirmed_api"
    assert rsa_f[0].key_size == "2048"


def test_comment_only_match_is_downgraded():
    code = "# cipher = algorithms.AES(key)\n"
    findings = RD.detect(code, "svc/x.py", "python")
    aes = [f for f in findings if f.algorithm == "AES"]
    assert aes
    assert aes[0].confidence != "confirmed_api"  # downgraded from a comment line


def test_prose_mentions_do_not_match():
    code = "We should stop using RSA and DES and MD5 someday.\n"
    findings = RD.detect(code, "notes.py", "python")
    assert findings == []


def test_dynamic_algorithm_extraction_node_crypto():
    code = "const h = crypto.createHash('sha1').update(x).digest('hex');\n"
    findings = run_detectors(code, "app/auth.js")
    algos = {normalize(f).algorithm for f in findings}
    assert "SHA-1" in algos


def test_config_tls_version_detected():
    cfg = "ssl_protocols TLSv1 TLSv1.2 TLSv1.3;\n"
    findings = RD.detect(cfg, "nginx.conf", "config")
    assert any(f.family == "protocol" for f in findings)


def test_normalize_canonicalises_names():
    from app.detection.rules import RawFinding

    n = normalize(RawFinding(algorithm="sha256", family="hash", primitive="hash",
                             confidence="confirmed_api", matched_indicator="x", signature_id="s"))
    assert n.algorithm == "SHA-256"
    assert n.algorithm_family == "hash"
