"""Credential redaction for markdown export.

Only PREFIX/STRUCTURE-KEYED credential shapes are matched -- vendor sentinels
like AKIA / ghp_ / xoxb- / sk-ant- whose anchor essentially cannot occur in
prose by accident -- plus PEM PRIVATE KEY blocks. There is deliberately NO
generic entropy, keyword-proximity, or base64/blob detection, so ordinary note
text, code, identifiers, public certificates, and embedded data are left intact
and the pass is effectively free of false positives.

Redaction replaces the credential with a visible marker (e.g. "[redacted:jwt]")
rather than deleting it: "a credential was here" is useful context for whoever
reads the exported markdown; the credential value itself is not.
"""

import re
from collections import Counter

# Vendor-sentinel-keyed credential shapes. (compiled pattern, replacement)
_SECRET_PATTERNS = (
    # AWS access key IDs (AKIA=long-lived, ASIA=STS, ABIA/ACCA variants).
    (re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b"), "[redacted:aws-key-id]"),
    # GitHub tokens: classic (ghp_/gho_/ghu_/ghs_/ghr_) and fine-grained.
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"), "[redacted:github-token]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,255}\b"), "[redacted:github-token]"),
    # GitLab personal access tokens.
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "[redacted:gitlab-token]"),
    # OpenAI / Anthropic style keys. Two branches so each is captured as one
    # full span (a single prefix-loop pattern locks its tail onto an interior
    # 32-char run and leaves the rest of a base64url key un-redacted):
    #   - OpenAI (sk- / sk-proj-): dashless base62 tail, so short kebab-case
    #     slugs like "sk-loading-spinner-dark" can't match.
    #   - Anthropic (sk-ant-<type><ver>-<body>): covers console API keys
    #     (sk-ant-api03-) and Claude.ai OAuth tokens (sk-ant-oat01-). The type
    #     segment is [a-z]+ followed by REQUIRED version digits (\d{2,}), which
    #     future-proofs new versions (api04, oat02, ...) and, crucially, is what
    #     separates a real key from an Ant-Design-style kebab class such as
    #     "sk-ant-design-system-..." (no fused digits -> no match). Body uses
    #     the base64url charset with a modest floor since the sk-ant-<x>NN-
    #     anchor is already highly specific.
    (
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b|\bsk-ant-[a-z]{2,12}\d{2,}-[A-Za-z0-9_-]{20,}\b"),
        "[redacted:api-key]",
    ),
    # Slack tokens + incoming-webhook paths.
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[redacted:slack-token]"),
    (
        re.compile(r"hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+"),
        "hooks.slack.com/services/[redacted:slack-webhook]",
    ),
    # Stripe secret/restricted keys (live AND test -- test keys still
    # grant API access to the test-mode account).
    (re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[redacted:stripe-key]"),
    # Google API keys.
    (re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"), "[redacted:google-api-key]"),
    # npm automation tokens.
    (re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), "[redacted:npm-token]"),
    # PyPI upload tokens (macaroon with fixed b64 "pypi.org" prefix).
    (re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{20,}\b"), "[redacted:pypi-token]"),
    # SendGrid API keys (SG.<22>.<43>).
    (re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b"), "[redacted:sendgrid-key]"),
    # Twilio API key SIDs (SK + 32 hex).
    (re.compile(r"\bSK[a-f0-9]{32}\b"), "[redacted:twilio-key]"),
    # JWTs -- three dot-joined base64url segments, first two decoding
    # from the literal '{"' ("eyJ").
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[redacted:jwt]",
    ),
    # Authorization: Bearer <token> header captures. {30,} floor keeps
    # doc placeholders (YOUR_TOKEN, $TOKEN, <token>) out of scope.
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-.=~+/]{30,}"), "Bearer [redacted:bearer-token]"),
)

# PEM PRIVATE KEY blocks (RSA/EC/DSA/OPENSSH/ENCRYPTED/PGP). Public
# certificates, public keys, and CSRs are meant to be shared and carry no
# secret, so they are deliberately left intact. No generic base64/blob rule
# is applied -- that would redact non-secret embedded images and encoded data.
_ARMOR_PATTERNS = (
    (
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----.*?"
            r"-----END [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----",
            re.DOTALL,
        ),
        "[redacted:private-key]",
    ),
)


def redact_secrets(text):
    """Redact credentials, returning (redacted_text, Counter of marker -> count).

    Applies the vendor-sentinel screen (API keys/tokens with recognizable
    prefixes) and PEM PRIVATE KEY blocks. Only high-confidence, structurally-
    anchored shapes are touched; public certs and embedded data are left intact.
    """
    counts = Counter()
    for pat, repl in _ARMOR_PATTERNS + _SECRET_PATTERNS:
        text, n = pat.subn(repl, text)
        if n:
            counts[repl.strip()] += n
    return text, counts


def redact_tree(obj):
    """Recursively redact every string *value* in a nested dict/list structure.

    Returns (new_obj, Counter). Dictionary keys are property names, not secrets,
    so they are left alone. Used to scrub the parsed document (headers,
    property sets) that backs the default dump and the JSON output.
    """
    counts = Counter()

    def walk(node):
        if isinstance(node, str):
            red, c = redact_secrets(node)
            counts.update(c)
            return red
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, tuple):
            return tuple(walk(v) for v in node)
        return node

    return walk(obj), counts


def redact_bytes(data):
    """Redact an embedded file's contents when it is UTF-8 text.

    Covers attachments that are really text (a pasted .pem, .env, config, or
    script). Binary attachments (images, Office docs) fail the strict decode and
    are returned untouched -- there is no text there to scrub, and rewriting
    their bytes could only corrupt them. Returns (bytes, Counter).
    """
    try:
        text = data.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return data, Counter()
    red, counts = redact_secrets(text)
    if not counts:
        return data, counts
    return red.encode("utf-8"), counts
