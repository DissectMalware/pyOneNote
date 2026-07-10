from pyOneNote.Header import *
from pyOneNote.FileNode import *

class OneDocment:
    def __init__(self, file):
        self._files = None
        self._properties= None
        self._global_identification_table= {}
        self.cur_revision = None
        self.header = Header(file)
        self.root_file_node_list = FileNodeList(file, self, self.header.fcrFileNodeListRoot)

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
        # ObjectDeclaration2LargeRefCountFND is used for objects whose
        # reference count doesn't fit in one byte (e.g. more heavily-shared
        # or larger page content), and the ReadOnly* variants wrap either
        # declaration with an extra md5Hash. All four carry the same
        # propertySet-bearing body and were previously excluded here, which
        # silently dropped any text stored under them.
        filters = [
            'ObjectDeclaration2RefCountFND',
            'ObjectDeclaration2LargeRefCountFND',
            'ReadOnlyObjectDeclaration2RefCountFND',
            'ReadOnlyObjectDeclaration2LargeRefCountFND',
        ]

        self._properties = []

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)
        for node in nodes:
            if hasattr(node, 'propertySet'):
                node.propertySet.body.indent= '\t\t'
                # ReadOnly* variants wrap the declaration in `.base`.
                decl_body = node.data.base.body if hasattr(node.data, 'base') else node.data.body
                self._properties.append({'type': str(decl_body.jcid), 'identity':str(decl_body.oid), 'val':node.propertySet.body.get_properties()})

        return  self._properties

    def get_files(self):
        if self._files:
            return self._files
        nodes = []
        self._files = {}
        filters = ["FileDataStoreObjectReferenceFND", "ObjectDeclarationFileData3RefCountFND"]

        OneDocment.traverse_nodes(self.root_file_node_list, nodes, filters)

        self.get_global_identification_table()

        for node in nodes:
            if hasattr(node, "data") and node.data:
                if isinstance(node.data, FileDataStoreObjectReferenceFND):
                    if not str(node.data.guidReference) in self._files:
                        self._files[str(node.data.guidReference)] = {"extension": "", "content": "", "identity": ""}
                    self._files[str(node.data.guidReference)]["content"] = node.data.fileDataStoreObject.FileData
                elif isinstance(node.data, ObjectDeclarationFileData3RefCountFND):
                    guid = node.data.FileDataReference.StringData.replace("<ifndf>{", "").replace("}", "")
                    guid = guid.lower()
                    if not guid in self._files:
                        self._files[guid] = {"extension": "", "content": "", "identity": ""}
                    self._files[guid]["extension"] = node.data.Extension.StringData
                    self._files[guid]["identity"] = str(node.data.oid)
        return self._files


    def get_global_identification_table(self):
        return self._global_identification_table

    def get_json(self):
        files_in_hex = {}
        for key, file in self.get_files().items():
            files_in_hex[key] = {'extension': file['extension'],
                                 'content': file['content'].hex(),
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



