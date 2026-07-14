# pyOneNote
pyOneNote is a lightweight python library to read OneNote files. The main goal of this parser is to allow cybersecurity analyst to extract useful information from OneNote files.

# Installing the parser

Installing the latest development

```
pip install -U https://github.com/DissectMalware/pyOneNote/archive/master.zip --force
```
# Running the parser

To dump all embedded file in current directory
```
pyonenote -f example.one 
```

To dump all embedded file in example.one into output_dir
```
pyonenote -f example.one -o output_dir 
```
To dump all embedded file in example.one into output_dir and add .bin to the end of each filename
```
pyonenote -f example.one -o output_dir -e bin
```

## Bulk markdown export

To extract the page text of a section to clean markdown (embedded null bytes
stripped, historical page revisions de-duplicated, one `##` heading per page):
```
pyonenote -m -f example.one -o output_dir
```

`-f` may also point at a directory, in which case every `.one` file in it is
exported to its own `<section>.md` inside `output_dir` — useful for dumping a
whole notebook's worth of sections in one pass for scripted diffing or pattern
extraction:
```
pyonenote -m -f "/path/to/OneNote Backup/MyNotebook" -o markdown_out
```

### Redacting secrets

Add `-r` / `--redact-secrets` to replace credentials with visible
`[redacted:*]` markers — useful when output will be shared for review:
```
pyonenote -r    -f "MyNotebook/Section.one"                 # default dump
pyonenote -r -j -f "MyNotebook/Section.one"                 # JSON
pyonenote -r -m -f "MyNotebook" -o markdown_out             # markdown
```
`-r` applies to **every output mode** — the default dump, JSON (`-j`), markdown
(`-m`), and any text attachment written to `--output-dir`. Binary attachments
(images, Office docs) contain no text to scrub and are written unchanged.

Redaction matches only high-confidence, structurally-anchored shapes (see
`pyOneNote/redact.py`), so ordinary note text is left untouched:
- **Vendor sentinels**: prefix/structure-keyed API keys and tokens —
  AWS/GitHub/GitLab/OpenAI/Anthropic/Slack/Stripe/Google/npm/PyPI/SendGrid/
  Twilio keys, JWTs, and `Authorization: Bearer` tokens.
- **PEM private keys**: `PRIVATE KEY` blocks (RSA/EC/DSA/OPENSSH/ENCRYPTED/PGP).
  Public certificates, public keys, and CSRs are meant to be shared and are left
  intact.

There is deliberately no generic entropy, keyword-proximity, or base64/blob
detection, so ordinary text and embedded data (images, encoded content) are left
untouched and the pass is effectively free of false positives.

A per-run summary reports how many credentials of each type were redacted.

# Command Line
```
usage: pyonenote [-h] -f FILE [-o OUTPUT_DIR] [-e EXTENSION] [-j] [-m] [-r]
```

Note: pyOneNote is under active development

# How to Contribute
If you found a bug or would like to suggest an improvement, please create a new issue on the [issues page](https://github.com/DissectMalware/pyOneNote/issues).

Feel free to contribute to the project forking the project and submitting a pull request.

You can reach [me (@DissectMlaware) on Twitter](https://twitter.com/DissectMalware) via a direct message.
