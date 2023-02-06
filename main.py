import Header
import FileNode
import sys
import os
from typing import BinaryIO
import logging

log = logging.getLogger()


def traverse_nodes(root_file_node_list, nodes, filters):
    for fragment in root_file_node_list.fragments:
        for file_node in fragment.fileNodes:
            if len(filters) == 0 or hasattr(file_node, 'data') and type(file_node.data).__name__ in filters:
                nodes.append(file_node)

            for child_file_node_list in file_node.children:
                traverse_nodes(child_file_node_list, nodes, filters)


def dump_files(file: BinaryIO, output_dir: str, extension: str=''):
    """
        file: open(x, "rb")
        output_dir: path where to store extracted files
        extension: add extension to extracted filename(s)
    """
    if file.read(16) != b"\xE4\x52\x5C\x7B\x8C\xD8\xA7\x4D\xAE\xB1\x53\x78\xD0\x29\x96\xD3":
        log.error("please provide valid One file")
        return

    header = Header.Header(file)
    root_file_node_list = FileNode.FileNodeList(file, header.fcrFileNodeListRoot)

    # nodes = []
    # filters = []
    # traverse_nodes(root_file_node_list, nodes, filters)
    # for node in nodes:
    #     if hasattr(node, 'data') and node.data:
    #         print(node.data)

    nodes = []
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    filters = ['FileDataStoreObjectReferenceFND',
               'ObjectDeclarationFileData3RefCountFND']

    traverse_nodes(root_file_node_list, nodes, filters)
    files = {}
    for node in nodes:
        if hasattr(node, 'data') and node.data:
            if isinstance(node.data, FileNode.FileDataStoreObjectReferenceFND):
                if not str(node.data.guidReference) in files:
                    files[ str(node.data.guidReference)] = {'extension':'', 'content':''}
                files[str(node.data.guidReference)]['content'] = node.data.fileDataStoreObject.FileData
            elif isinstance(node.data, FileNode.ObjectDeclarationFileData3RefCountFND):
                guid = node.data.FileDataReference.StringData.replace('<ifndf>{', '').replace('}', '')
                guid = guid.lower()
                if not guid in files:
                    files[guid] = {'extension':'', 'content':''}
                files[guid]['extension'] = node.data.Extension.StringData

    counter = 0

    if extension and not extension.startswith('.'):
        extension = '.' + extension

    for file_guid in files:
        print('{}, {}, {},\t\t{}'.format(file_guid,
                                  files[file_guid]['extension'],
                                  len(files[file_guid]['content']),
                                  files[file_guid]['content'][:128].hex()))

        with open(os.path.join(output_dir, 'file_{}{}{}'.format(
            counter,
            files[file_guid]['extension'],
            extension
        )), 'wb') as output_file:
            output_file.write(files[file_guid]['content'])
        counter += 1



if __name__ == '__main__':

    if len(sys.argv) < 2:
        exit()

    output_dir ='./'

    if len(sys.argv) == 3:
        output_dir = sys.argv[2]

    extension = ''
    if len(sys.argv) == 4:
        extension = sys.argv[3]

    with open(sys.argv[1], 'rb') as file:
        dump_files(file, output_dir, extension)
