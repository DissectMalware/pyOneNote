"""Regression tests for pyOneNote.redact secret patterns.

Run with:  python3 -m unittest discover -s tests
(stdlib unittest only -- no third-party test runner required.)

The sk- (OpenAI/Anthropic) rule is the sharp edge: an earlier single
prefix-loop pattern would lock its {32,} tail onto an interior run of a
base64url Anthropic key and redact only that chunk, silently leaving the
rest of the live key in the output. These tests assert FULL-SPAN redaction
(the whole key token is gone), not merely that a match occurred.
"""
import json
import os
import random
import string
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyOneNote.redact import redact_secrets, redact_tree, redact_bytes  # noqa: E402

MARKER = "[redacted:api-key]"
B64URL = string.ascii_letters + string.digits + "-_"
BASE62 = string.ascii_letters + string.digits


def _redacted_line(secret):
    """Redact a line that is exactly the secret; return the stripped result."""
    out, counts = redact_secrets(secret)
    return out.strip(), counts


class SkKeyRedaction(unittest.TestCase):
    def test_openai_classic_full_span(self):
        key = "sk-" + "".join(random.Random(1).choice(BASE62) for _ in range(48))
        out, counts = _redacted_line(key)
        self.assertEqual(out, MARKER)          # whole token replaced
        self.assertNotIn("sk-", out)           # no residual key material
        self.assertEqual(counts[MARKER], 1)

    def test_openai_project_full_span(self):
        key = "sk-proj-" + "".join(random.Random(2).choice(BASE62) for _ in range(48))
        out, _ = _redacted_line(key)
        self.assertEqual(out, MARKER)

    def test_anthropic_base64url_full_span_bulk(self):
        # The regression: across many realistic keys, EVERY key must be fully
        # redacted with no leaked tail. The old pattern managed ~21% full.
        # Cover both documented token types (console api03, OAuth oat01) and
        # future version digits (api04, oat02, ...). Bodies end alphanumeric,
        # as real keys do (…AA), so no trailing-dash trim artifact.
        rng = random.Random(7)
        for _ in range(500):
            kind = rng.choice(("api", "oat", "admin"))
            ver = "0%d" % rng.randint(1, 9)
            length = rng.randint(20, 95)
            body = "".join(rng.choice(B64URL) for _ in range(length))
            body = body.rstrip("-") + rng.choice(BASE62)  # real keys end alnum
            key = "sk-ant-%s%s-%s" % (kind, ver, body)
            out, counts = _redacted_line(key)
            self.assertEqual(out, MARKER, "partial/missed redaction leaks key material")
            self.assertEqual(counts[MARKER], 1)

    def test_anthropic_oauth_and_future_versions(self):
        for key in (
            "sk-ant-oat01-" + "".join(random.Random(3).choice(B64URL) for _ in range(60)) + "Az",
            "sk-ant-api04-" + "".join(random.Random(4).choice(B64URL) for _ in range(80)) + "Az",
            "sk-ant-api100-" + "".join(random.Random(5).choice(B64URL) for _ in range(80)) + "Az",
        ):
            out, _ = _redacted_line(key)
            self.assertEqual(out, MARKER)

    def test_anthropic_embedded_in_prose(self):
        rng = random.Random(11)
        body = "".join(rng.choice(B64URL) for _ in range(93)) + "AA"
        key = "sk-ant-api03-" + body
        line = "ANTHROPIC_API_KEY=" + key + "  # rotate me"
        out, _ = redact_secrets(line)
        self.assertIn(MARKER, out)
        self.assertNotIn(key, out)
        # no non-trivial fragment of the key survives
        self.assertNotIn(body[:40], out)


class SkFalsePositives(unittest.TestCase):
    def test_kebab_css_class_not_redacted(self):
        s = 'class="sk-loading-spinner-overlay-fullscreen-darkmode"'
        out, counts = redact_secrets(s)
        self.assertEqual(out, s)
        self.assertNotIn(MARKER, out)

    def test_short_sk_identifier_not_redacted(self):
        s = "sk-loader"
        out, _ = redact_secrets(s)
        self.assertEqual(out, s)

    def test_ant_design_kebab_class_not_redacted(self):
        # "ant" collides with Ant Design's class prefix; the required fused
        # version digits (api03) are what keep these kebab classes out.
        for s in (
            "class='sk-ant-design-system-really-long-classname-wrapper'",
            "sk-ant-col-24-responsive-grid-column-layout-helper-xl",
            "sk-ant-btn",
        ):
            out, counts = redact_secrets(s)
            self.assertEqual(out, s)
            self.assertNotIn(MARKER, out)


class PemArmor(unittest.TestCase):
    def _block(self, label):
        body = "\n".join("MIID" + "A" * 60 for _ in range(20))
        return "-----BEGIN %s-----\n%s\n-----END %s-----" % (label, body, label)

    def test_private_keys_redacted(self):
        for label in (
            "PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY",
            "OPENSSH PRIVATE KEY", "ENCRYPTED PRIVATE KEY", "PGP PRIVATE KEY BLOCK",
        ):
            out, counts = redact_secrets(self._block(label))
            self.assertEqual(counts["[redacted:private-key]"], 1, label)
            self.assertNotIn("MIID" + "A" * 60, out)

    def test_public_material_left_intact(self):
        # Public certs / keys / CSRs are shareable and must NOT be redacted,
        # and with no generic base64 rule their bodies survive too.
        for label in ("CERTIFICATE", "PUBLIC KEY", "CERTIFICATE REQUEST"):
            block = self._block(label)
            out, counts = redact_secrets(block)
            self.assertEqual(out, block, label)
            self.assertEqual(len(counts), 0, label)

    def test_embedded_base64_not_redacted(self):
        # A long base64 blob (e.g. an embedded image) is not a credential.
        blob = "data = '" + "QUJD" * 200 + "'"
        out, _ = redact_secrets(blob)
        self.assertEqual(out, blob)


class TreeAndBytesRedaction(unittest.TestCase):
    """Redaction must cover every output mode, not just markdown: the default
    dump and JSON both render the parsed tree, and attachments are written to
    disk. Partial coverage would leak in the modes that aren't scrubbed."""

    def test_redact_tree_scrubs_nested_string_values(self):
        key = "sk-" + "A1b2C3d4" * 6  # 48-char base62 tail
        tree = {
            "headers": {"guidFile": "1234-abcd", "count": 7},
            "properties": [
                {"type": "jcidRichTextOENode",
                 "val": {"RichEditTextUnicode": "aws key AKIAABCDEFGHIJKLMNOP here"}},
                {"type": "jcidTitleNode", "val": {"RichEditTextUnicode": "token " + key}},
            ],
        }
        out, counts = redact_tree(tree)
        blob = json.dumps(out)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", blob)
        self.assertNotIn(key, blob)
        self.assertIn("[redacted:aws-key-id]", blob)
        self.assertIn(MARKER, blob)
        self.assertEqual(sum(counts.values()), 2)
        # non-string values and dict keys survive untouched
        self.assertEqual(out["headers"]["count"], 7)
        self.assertEqual(out["properties"][0]["type"], "jcidRichTextOENode")

    def test_redact_tree_leaves_clean_text_alone(self):
        tree = {"properties": [{"val": {"RichEditTextUnicode": "just some notes"}}]}
        out, counts = redact_tree(tree)
        self.assertEqual(out, tree)
        self.assertEqual(sum(counts.values()), 0)

    def test_redact_bytes_scrubs_text_attachment(self):
        pem = (b"-----BEGIN RSA PRIVATE KEY-----\n"
               + b"MIIB" + b"B" * 60 + b"\n-----END RSA PRIVATE KEY-----\n")
        out, counts = redact_bytes(pem)
        self.assertIn(b"[redacted:private-key]", out)
        self.assertNotIn(b"MIIB" + b"B" * 60, out)
        self.assertEqual(counts["[redacted:private-key]"], 1)

    def test_redact_bytes_leaves_binary_untouched(self):
        # A PNG header is not valid UTF-8; it must pass through byte-identical.
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe\xfd"
        out, counts = redact_bytes(png)
        self.assertEqual(out, png)
        self.assertEqual(sum(counts.values()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
