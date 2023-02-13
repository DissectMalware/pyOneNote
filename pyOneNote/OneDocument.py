from pyOneNote.Header import *
from pyOneNote.FileNode import *
import json


class OneDocment:
    def __init__(self, file):
        self.header = Header(file)
        self.root_file_node_list = FileNodeList(file, self.header.fcrFileNodeListRoot)
        self._files = None
        self._properties= None


    [staticmethod]
    def traverse_nodes(root_file_node_list, nodes, filters):
        for fragment in root_file_node_list.fragments:
            for file_node in fragment.fileNodes:
                if len(filters) == 0 or hasattr(file_node, "data") and type(file_node.data).__name__ in filters:
                    nodes.append(file_node)

                for child_file_node_list in file_node.children:
                    OneDocment.traverse_nodes(child_file_node_list, nodes, filters)

    def get_properties(self):
        if self._properties:
            return self._properties
        nodes = []
        filters = ['ObjectDeclaration2RefCountFND']

        self._properties = {}

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)
        for node in nodes:
            if hasattr(node, 'propertySet'):
                if not str(node.data.body.jcid) in self._properties:
                    self._properties[str(node.data.body.jcid)] = []
                node.propertySet.body.indent= '\t\t'
                self._properties[str(node.data.body.jcid)].append(str(node.propertySet.body))

        return  self._properties

    def get_files(self):
        if self._files:
            return self._files
        nodes = []
        self._files = {}
        filters = ["FileDataStoreObjectReferenceFND", "ObjectDeclarationFileData3RefCountFND"]

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)

        for node in nodes:
            if hasattr(node, "data") and node.data:
                if isinstance(node.data, FileDataStoreObjectReferenceFND):
                    if not str(node.data.guidReference) in self._files:
                        self._files[str(node.data.guidReference)] = {"extension": "", "content": ""}
                    self._files[str(node.data.guidReference)]["content"] = node.data.fileDataStoreObject.FileData
                elif isinstance(node.data, ObjectDeclarationFileData3RefCountFND):
                    guid = node.data.FileDataReference.StringData.replace("<ifndf>{", "").replace("}", "")
                    guid = guid.lower()
                    if not guid in self._files:
                        self._files[guid] = {"extension": "", "content": ""}
                    self._files[guid]["extension"] = node.data.Extension.StringData
        return self._files

    def get_json(self):
        files_in_hex = {}
        for key, file in self.get_files().items():
            files_in_hex[key] = {'extension': file['extension'],
                                 'content': file['content'].hex()}

        res = {
            "headers": self.header.convert_to_dictionary(),
            "properties": self.get_properties(),
            "files": files_in_hex,
        }

        return res

    def __str__(self):
        return '{}\n{}\n{}'.format(str(self.header),
                                   str(self.rootFileNode))
