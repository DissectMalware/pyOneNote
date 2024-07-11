from pyOneNote.Header import *
from pyOneNote.FileNode import *
from pyOneNote.OneDocument import *
import math
import sys
import os
import logging
import argparse
import json

log = logging.getLogger()

def check_valid(file):
    if file.read(16) in (
        b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3",
        b"\xA1\x2F\xFF\x43\xD9\xEF\x76\x4C\x9E\xE2\x10\xEA\x57\x22\x76\x5F",
    ):
        return True
    return False


def process_onenote_file(file, output_dir, extension, json_output, preserve_filenames):
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
        file_metadata = {}
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
        if preserve_filenames:
            filename_counters = {}

        for file_guid, file in document.get_files().items():
            filename = "file_{}{}{}".format(counter, file["extension"], extension)
            if preserve_filenames and file['identity'] in file_metadata:
                if file_metadata[file['identity']].get("EmbeddedFileName"):
                    filename = file_metadata[file['identity']]["EmbeddedFileName"]
                elif file_metadata[file['identity']].get("ImageFileName"):
                    filename = file_metadata[file['identity']]["ImageFileName"]

                filename = filename.replace('\x00', '')

                if filename not in filename_counters:
                    filename_counters[filename] = 0
                else:
                    filename_counters[filename] += 1
                    ext_index = filename.index(extension)
                    filename = "{} ({}){}".format(filename[:ext_index], filename_counters[filename], filename[ext_index:])

            with open(os.path.join(output_dir, filename), "wb") as output_file:
                output_file.write(file["content"])

            counter += 1

    return json.dumps(data)


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
    p.add_argument("-p", "--preserve-filenames", action="store_true", default=False, 
                   help="Preserve original filename(s) (when available) for extracted files")

    args = p.parse_args()

    if not os.path.exists(args.file):
        sys.exit("File: %s doesn't exist", args.file)

    with open(args.file, "rb") as file:
        process_onenote_file(file, args.output_dir, args.extension, args.json, args.preserve_filenames)
        

if __name__ == "__main__":
    main()


