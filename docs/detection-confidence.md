# How detection confidence works (analyst guide)

Every cryptographic asset in the CBOM carries a **detection confidence** — how sure ECDAT is
that the asset is really used, not just mentioned. It is the *highest* confidence among the
asset's evidence occurrences.

| Level | Meaning | Typical source | How to treat it |
|---|---|---|---|
| `confirmed_api` | An unambiguous cryptographic API call or import was matched, on a real code line (not a comment/string). | `rsa.generate_private_key(...)`, `Cipher.getInstance("AES/GCM/NoPadding")`, `crypto.createHash('sha256')`, a manifest declaring a known crypto library. | Trust it. This is a genuine usage. |
| `strong_textual` | A strong crypto keyword in a meaningful context, but not a verified call — e.g. a cipher-suite string in a config, a JWT `algorithm:` field, an API call that appeared only inside a comment. | Config files, TLS/SSH directives, commented-out code. | Very likely real; verify the surrounding config/code. |
| `weak_textual` | A bare algorithm name in a place it *could* be incidental. | Generic `key: value` config pairs, loosely-matched tokens. | Confirm manually before acting. ECDAT drops the weakest of these (unresolved generic key/value hits with no recognisable primitive) so they never enter the CBOM. |
| `ml_classified` | A machine-learning classifier predicted a cryptographic operation for an ambiguous snippet. | (Interface present; no ML model ships in this build.) | Always review the retained evidence; never treat as confirmed. |

## The AST / comment heuristic

The rule detector runs a lightweight check that stands in for a full AST pass: if a pattern
matches only on a **comment or bare-string line** in a real code file, its confidence is
lowered one level (`confirmed_api → strong_textual`, etc.). Prose that merely names algorithms
(`"we should stop using DES"`) matches no API pattern and produces **no asset at all**.

To raise fidelity, register a tree-sitter detector (confirms the match is a call node) or an ML
classifier in `app/detection/rules.py::DETECTORS` — the CBOM schema and every downstream engine
are unchanged.

## Binary & container findings

`strings`-based binary matches and Dockerfile package inventories are always emitted at
`weak_textual` (binary) or below. They tell you a capability is *present in the artifact*, not
that a specific call site uses it.

## Reading evidence

Open any asset → the drawer lists every occurrence: file/line, the matched token, the
enclosing function/scope, a context snippet, the detector, and the signature id
(`crypto_signatures.yaml` entry). Reports include the same occurrences.
