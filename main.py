import Header
import FileNode
import sys
import os
import logging
from typing import BinaryIO

log = logging.getLogger()


def traverse_nodes(root_file_node_list, nodes, filters):
    for fragment in root_file_node_list.fragments:
        for file_node in fragment.fileNodes:
            if len(filters) == 0 or hasattr(file_node, "data") and type(file_node.data).__name__ in filters:
                nodes.append(file_node)

            for child_file_node_list in file_node.children:
                traverse_nodes(child_file_node_list, nodes, filters)


def print_all_properties(root_file_node_list):
    nodes = []
    count = 0
    filters = ['ObjectDeclaration2RefCountFND']

    traverse_nodes(root_file_node_list, nodes, filters)
    for node in nodes:
        if hasattr(node, 'propertySet'):
            print(str(node.data.body.jcid))
            print(node.propertySet.body)


def dump_files(root_file_node_list:FileNode.FileNodeList, output_dir: str, extension: str = ""):
    """
    file: open(x, "rb")
    output_dir: path where to store extracted files
    extension: add extension to extracted filename(s)
    """

    nodes = []
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    filters = ["FileDataStoreObjectReferenceFND", "ObjectDeclarationFileData3RefCountFND"]

    traverse_nodes(root_file_node_list, nodes, filters)
    files = {}
    for node in nodes:
        if hasattr(node, "data") and node.data:
            if isinstance(node.data, FileNode.FileDataStoreObjectReferenceFND):
                if not str(node.data.guidReference) in files:
                    files[str(node.data.guidReference)] = {"extension": "", "content": ""}
                files[str(node.data.guidReference)]["content"] = node.data.fileDataStoreObject.FileData
            elif isinstance(node.data, FileNode.ObjectDeclarationFileData3RefCountFND):
                guid = node.data.FileDataReference.StringData.replace("<ifndf>{", "").replace("}", "")
                guid = guid.lower()
                if not guid in files:
                    files[guid] = {"extension": "", "content": ""}
                files[guid]["extension"] = node.data.Extension.StringData

    counter = 0

    if extension and not extension.startswith("."):
        extension = "." + extension

    for file_guid in files:
        print(
            "{}, {}, {},\t\t{}".format(
                file_guid, files[file_guid]["extension"], len(files[file_guid]["content"]), files[file_guid]["content"][:128].hex()
            )
        )

        with open(
            os.path.join(output_dir, "file_{}{}{}".format(counter, files[file_guid]["extension"], extension)), "wb"
        ) as output_file:
            output_file.write(files[file_guid]["content"])
        counter += 1


def check_valid(file):
    if file.read(16) in (
        b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3",
        b"\xA1\x2F\xFF\x43\xD9\xEF\x76\x4C\x9E\xE2\x10\xEA\x57\x22\x76\x5F",
    ):
        return True
    return False


def process_onenote_file(file, output_dir, extension):
    if not check_valid(file):
        log.error("please provide valid One file")
        exit()

    file.seek(0)
    header = Header.Header(file)
    root_file_node_list = FileNode.FileNodeList(file, header.fcrFileNodeListRoot)
    print_all_properties(root_file_node_list)
    dump_files(root_file_node_list, output_dir, extension)



if __name__ == "__main__":

    if len(sys.argv) < 2:
        exit()

    output_dir = "./"

    if len(sys.argv) == 3:
        output_dir = sys.argv[2]

    extension = ""
    if len(sys.argv) == 4:
        extension = sys.argv[3]

    if not os.path.exists(sys.argv[1]):
        log.error("File %s doesn't exist", sys.argv[1])
        exit()

    with open(sys.argv[1], "rb") as file:

        process_onenote_file(file, output_dir, extension)

