from pyOneNote.Header import *
from pyOneNote.FileNode import *
from pyOneNote.OneDocument import *
import math
import sys
import os
import logging
import argparse
import json
from collections import Counter

log = logging.getLogger()

def check_valid(file):
    if file.read(16) in (
        b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3",
        b"\xA1\x2F\xFF\x43\xD9\xEF\x76\x4C\x9E\xE2\x10\xEA\x57\x22\x76\x5F",
    ):
        return True
    return False


def process_onenote_file(file, output_dir, extension, json_output, redact=False):
    if not check_valid(file):
        log.error("please provide valid One file")
        exit()

    file.seek(0)
    document = OneDocment(file)
    data = document.get_json()

    if redact:
        from pyOneNote.redact import redact_tree, redact_bytes
        counts = Counter()
        for section in ("headers", "properties"):
            data[section], section_counts = redact_tree(data[section])
            counts.update(section_counts)
        # Embedded attachments that are really text (a pasted .pem/.env/config)
        # are scrubbed too; binary attachments have no text to redact. Mutating
        # the document's file cache also covers the extraction loop below.
        for key, embedded in document.get_files().items():
            content, file_counts = redact_bytes(embedded["content"])
            embedded["content"] = content
            data["files"][key]["content"] = content.hex()
            counts.update(file_counts)
        n = sum(counts.values())
        # stderr, so it can never corrupt the JSON on stdout
        print("Redacted {} credential(s){}".format(
            n, ": " + ", ".join("{} {}".format(v, k) for k, v in counts.most_common()) if n else ""),
            file=sys.stderr)

    if not json_output:
        print('Headers\n####################################################################')
        indent = '\t'
        for key, header in data['headers'].items():
            print('{}{}: {}'.format(indent, key, header))

        print('\n\nProperties\n####################################################################')
        indent = '\t'
        file_metadata ={}
        for propertySet in data['properties']:
            print('{}{}({}):'.format(indent, propertySet['type'], propertySet['identity']))
            if propertySet['type'] == "jcidEmbeddedFileNode":
                if 'EmbeddedFileContainer' in propertySet['val']:
                    file_metadata[propertySet['val']['EmbeddedFileContainer'][0]] = propertySet['val']
            if propertySet['type'] == "jcidImageNode":
                if 'PictureContainer' in propertySet['val']:
                    file_metadata[propertySet['val']['PictureContainer'][0]] = propertySet['val']


            for property_name, property_val in propertySet['val'].items():
                print('{}{}: {}'.format(indent+'\t', property_name, str(property_val)))
            print("")

        print('\n\nEmbedded Files\n####################################################################')
        indent = '\t'
        for name, file in data['files'].items():
            print('{}{} ({}):'.format(indent, name, file['identity']))
            print('\t{}Extension: {}'.format(indent, file['extension']))
            if(file['identity'] in file_metadata):
                for property_name, property_val in file_metadata[file['identity']].items():
                    print('{}{}: {}'.format(indent+'\t', property_name, str(property_val)))
            print('{}'.format( get_hex_format(file['content'][:256], 16, indent+'\t')))

        if extension and not extension.startswith("."):
            extension = "." + extension

        counter = 0
        for file_guid, file in document.get_files().items():
            with open(
                    os.path.join(output_dir,
                                 "file_{}{}{}".format(counter, file["extension"], extension)), "wb"
            ) as output_file:
                output_file.write(file["content"])
            counter += 1

    return json.dumps(data)


def export_markdown(file, output_path, section_title, redact=False):
    if not check_valid(file):
        log.error("skipping invalid .one file: %s", section_title)
        return None, None
    file.seek(0)
    document = OneDocment(file)
    result = document.get_markdown(section_title, redact=redact)
    markdown, redactions = result if redact else (result, None)
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(markdown)
    page_count = len(document.get_pages())
    log.info("wrote %d pages -> %s", page_count, output_path)
    return page_count, redactions


def bulk_export_markdown(input_path, output_dir, redact=False):
    """Export one .one file, or every .one file in a directory, to markdown."""
    os.makedirs(output_dir, exist_ok=True)
    if os.path.isdir(input_path):
        one_files = sorted(
            os.path.join(input_path, name)
            for name in os.listdir(input_path)
            if name.lower().endswith(".one")
        )
    else:
        one_files = [input_path]

    if not one_files:
        sys.exit("No .one files found in: %s" % input_path)

    total_pages = 0
    total_redactions = Counter()
    for one_file in one_files:
        section_title = os.path.splitext(os.path.basename(one_file))[0]
        output_path = os.path.join(output_dir, section_title + ".md")
        with open(one_file, "rb") as fh:
            pages, redactions = export_markdown(fh, output_path, section_title, redact=redact)
        if pages:
            total_pages += pages
            note = ""
            if redactions:
                total_redactions.update(redactions)
                note = "  [{} secrets redacted]".format(sum(redactions.values()))
            print("{}: {} pages -> {}{}".format(section_title, pages, output_path, note))
    print("\nDone. {} file(s), {} unique pages total.".format(len(one_files), total_pages))
    if redact:
        n = sum(total_redactions.values())
        print("Redacted {} credential(s) total{}".format(
            n, ": " + ", ".join("{} {}".format(v, k) for k, v in total_redactions.most_common()) if n else ""))


def get_hex_format(hex_str, col, indent):
    res = ''
    chars = (col*2)
    for i in range(math.ceil( len(hex_str)/chars)):
        segment = hex_str[i*chars: (i+1)*chars]
        res += indent + ' '.join([segment[i:i+2] for i in range(0, len(segment), 2)]) +'\n'
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--file", action="store", help="File to analyze", required=True)
    p.add_argument("-o", "--output-dir", action="store", default="./", help="Path where store extracted files")
    p.add_argument("-e", "--extension", action="store", default="", help="Append this extension to extracted file(s)")
    p.add_argument("-j", "--json", action="store_true", default=False, help="Generate JSON output only, no dumps or prints")
    p.add_argument("-m", "--markdown", action="store_true", default=False, help="Bulk-export page text to clean markdown. -f may be a single .one file or a directory of them; one .md is written per section into --output-dir")
    p.add_argument("-r", "--redact-secrets", action="store_true", default=False, help="Replace high-confidence credential shapes (AWS/GitHub/Slack/JWT/private keys, etc.) with [redacted:*] markers. Applies to every output mode: the default dump, JSON (-j), markdown (-m), and text attachments written to --output-dir")

    args = p.parse_args()

    if not os.path.exists(args.file):
        sys.exit("File: %s doesn't exist", args.file)

    if args.markdown:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        bulk_export_markdown(args.file, args.output_dir, redact=args.redact_secrets)
        return

    with open(args.file, "rb") as file:
        process_onenote_file(file, args.output_dir, args.extension, args.json, redact=args.redact_secrets)
        

if __name__ == "__main__":
    main()


