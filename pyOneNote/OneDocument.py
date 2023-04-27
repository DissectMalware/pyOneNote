from pyOneNote.Header import *
from pyOneNote.FileNode import *


class OneDocment:
    def __init__(self, file):
        self._files = None
        self._properties = None
        self._global_identification_table = {}
        self.cur_revision = None
        self.header = Header(file)
        self.root_file_node_list = FileNodeList(file, self, self.header.fcrFileNodeListRoot)

    @staticmethod
    def traverse_nodes(root_file_node_list, nodes, filters):
        for fragment in root_file_node_list:
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

        self._properties = []

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)
        for node in nodes:
            if hasattr(node, 'propertySet'):
                node.propertySet.body.indent = '\t\t'
                self._properties.append({'type': str(node.data.body.jcid), 'identity':str(node.data.body.oid), 'val':node.propertySet.body.get_properties()})

        return self._properties

    def get_files(self):
        nodes = []
        files = {}
        filters = ["FileDataStoreObjectReferenceFND", "ObjectDeclarationFileData3RefCountFND"]

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)

        self.get_global_identification_table()

        for node in nodes:
            if hasattr(node, "data") and node.data:
                if isinstance(node.data, FileDataStoreObjectReferenceFND):
                    if not str(node.data.guidReference) in files:
                        files[str(node.data.guidReference)] = {"extension": "", "content": "", "identity": ""}
                    files[str(node.data.guidReference)]["content"] = node
                elif isinstance(node.data, ObjectDeclarationFileData3RefCountFND):
                    guid = node.data.FileDataReference.StringData.replace("<ifndf>{", "").replace("}", "")
                    guid = guid.lower()
                    if not guid in files:
                        files[guid] = {"extension": "", "content": "", "identity": ""}
                    files[guid]["extension"] = node.data.Extension.StringData
                    files[guid]["identity"] = str(node.data.oid)

        for guid, file in files.items():
            yield guid, {
                "extension": file["extension"],
                "content": file["content"].data.fileDataStoreObject,
                "identity": file["identity"]
            }

    def get_global_identification_table(self):
        return self._global_identification_table

    def get_json(self):
        files_in_hex = {}
        for key, file in self.get_files():
            files_in_hex[key] = {'extension': file['extension'],
                                 'content': file['content'].read_content().hex(),
                                 'identity': file['identity']}

        res = {
            "headers": self.header.convert_to_dictionary(),
            "properties": self.get_properties(),
            "files": files_in_hex,
        }

        return res

    def __str__(self):
        return '{}\n{}\n{}'.format(str(self.header),
                                   str(self.rootFileNode))
