from pyOneNote.Header import *
from pyOneNote.FileNode import *
from pyOneNote.OneDocument import *
import sys
import os
import logging
import argparse

log = logging.getLogger()

def check_valid(file):
    if file.read(16) in (
        b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3",
        b"\xA1\x2F\xFF\x43\xD9\xEF\x76\x4C\x9E\xE2\x10\xEA\x57\x22\x76\x5F",
    ):
        return True
    return False


def process_onenote_file(file, output_dir, extension, json_output):
    if not check_valid(file):
        log.error("please provide valid One file")
        exit()

    file.seek(0)
    document = OneDocment(file)
    data = document.get_json()
    if not json_output:
        print('Headers\n####################################################################')
        indent = '\t'
        for key, header in data['headers'].items():
            print('{}{}: {}'.format(indent, key, header))

        print('\n\nProperties\n####################################################################')
        indent = '\t'
        for key, properties in data['properties'].items():
            for property in properties:
                print('{}{}:\n{}'.format(indent, key, property))

    return json.dumps(document.get_json())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--file", action="store", help="File to analyze", required=True)
    p.add_argument("-o", "--output-dir", action="store", default="./", help="Path where store extracted files")
    p.add_argument("-e", "--extension", action="store", default="", help="Append this extension to extracted file(s)")
    p.add_argument("-j", "--json", action="store_true", default=False, help="Generate JSON output only, no dumps or prints")

    args = p.parse_args()

    if not os.path.exists(args.file):
        sys.exit("File: %s doesn't exist", args.file)

    with open(args.file, "rb") as file:
        process_onenote_file(file, args.output_dir, args.extension, args.json)
        

if __name__ == "__main__":
    main()


