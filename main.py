import uuid
import struct
import Header
import FileNode
import sys


def traverse_nodes(root_file_node_list, nodes, filters):
    for fragment in root_file_node_list.fragments:
        for file_node in fragment.fileNodes:
            if len(filters) == 0 or hasattr(file_node, 'data') and type(file_node.data).__name__ in filters:
                nodes.append(file_node)

            for child_file_node_list in file_node.children:
                traverse_nodes(child_file_node_list, nodes, filters)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        exit()

    filters = []

    if len(sys.argv) == 3:
        filters = set(sys.argv[2].split(','))

    with open(sys.argv[1], 'rb') as file:
        header = Header.Header(file)
        root_file_node_list = FileNode.FileNodeList(file, header.fcrFileNodeListRoot)

        nodes = []
        traverse_nodes(root_file_node_list, nodes, filters)
        for node in nodes:
            if hasattr(node, 'data') and node.data:
                print(str(node.data))




