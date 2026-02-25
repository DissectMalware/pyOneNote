from pyOneNote.parser import OneNoteParser
import math
import sys
import os
import logging
import argparse
import json

log = logging.getLogger()


def get_hex_format(hex_str, col, indent):
    res = ''
    chars = (col*2)
    for i in range(math.ceil( len(hex_str)/chars)):
        segment = hex_str[i*chars: (i+1)*chars]
        res += indent + ' '.join([segment[i:i+2] for i in range(0, len(segment), 2)]) +'\n'
    return res


def process_onenote_file(file_path, output_dir, extension, json_output):
    """
    Process a OneNote file using the OneNoteParser API.
    
    Args:
        file_path (str): Path to the .one file
        output_dir (str): Directory to save extracted files
        extension (str): Optional extension to append to extracted files
        json_output (bool): If True, only return JSON; if False, print detailed output
        
    Returns:
        str: JSON representation of the document
    """
    try:
        parser = OneNoteParser(file_path)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Error opening file: {e}")
        exit(1)
    
    data = parser.get_json()
    
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
            print('{}'.format(get_hex_format(file['content'][:256], 16, indent+'\t')))

        parser.save_files(output_dir, extension)

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

    args = p.parse_args()

    if not os.path.exists(args.file):
        sys.exit("File: %s doesn't exist", args.file)

    with open(args.file, "rb") as file:
        process_onenote_file(file, args.output_dir, args.extension, args.json)
        

if __name__ == "__main__":
    main()


