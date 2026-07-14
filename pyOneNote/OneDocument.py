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

    # jcids that carry displayable text runs, in the order OneNote lays them out.
    _TEXT_JCIDS = ('jcidRichTextOENode', 'jcidTitleNode', 'jcidNumberListNode')

    @staticmethod
    def _run_text(val):
        # A single text run stores its content under one of these keys depending
        # on platform: RichEditTextUnicode (Windows, UTF-16) or TextExtendedAscii
        # (OneNote for Mac, latin-1). Strip embedded null bytes either way.
        text = val.get('RichEditTextUnicode') or val.get('TextExtendedAscii') or ''
        return text.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n').rstrip()

    def _toc_titles(self):
        # OneNote maintains a CachedTitleString for every page (used to render
        # the section's page tabs). Collecting them gives the authoritative set
        # of real page names, which we use to distinguish a page's title run
        # from its body runs.
        titles = set()
        for prop in self.get_properties():
            cached = prop['val'].get('CachedTitleString')
            if cached:
                cached = cached.replace('\x00', '').strip()
                if cached:
                    titles.add(cached)
        return titles

    def get_pages(self):
        """Reconstruct de-duplicated pages from the property stream.

        OneNote keeps every historical revision of a page in the same file, so
        the raw stream repeats each page 2-20x. We segment on jcidPageNode, pick
        the page's title as the first run matching a known CachedTitleString,
        then key pages by that title. Revisions of the same page collapse into
        one entry (identical runs de-duplicated), while genuinely distinct pages
        that happen to share text are preserved because de-dup is scoped per
        title. Pages are returned in first-seen order.
        """
        toc = self._toc_titles()

        # segment the flat stream into per-revision run lists
        raw_pages = []
        current = None
        for prop in self.get_properties():
            ptype = prop['type']
            if ptype == 'jcidPageNode':
                if current is not None:
                    raw_pages.append(current)
                current = []
                continue
            if current is None:
                continue
            if ptype in self._TEXT_JCIDS:
                text = self._run_text(prop['val'])
                if text:
                    current.append(text)
        if current is not None:
            raw_pages.append(current)

        pages = []
        by_title = {}
        for runs in raw_pages:
            if not runs:
                continue
            title = next((r for r in runs if r in toc), runs[0])
            if title not in by_title:
                entry = {'title': title, 'lines': [], '_seen': set()}
                by_title[title] = entry
                pages.append(entry)
            entry = by_title[title]
            for run in runs:
                if run == title or run in entry['_seen']:
                    continue
                entry['_seen'].add(run)
                entry['lines'].append(run)

        for entry in pages:
            del entry['_seen']
        return pages

    def get_markdown(self, section_title=None, redact=False):
        """Render every unique page in this document as a single markdown string.

        When redact is True, high-confidence credential shapes are replaced with
        visible [redacted:*] markers (see pyOneNote.redact). Returns the markdown
        string, or (string, Counter) of redaction counts when redact is True.
        """
        out = []
        if section_title:
            out.append('# {}\n'.format(section_title))
        for page in self.get_pages():
            title = page['title'].strip() or 'Untitled'
            out.append('## {}\n'.format(title))
            body = '\n'.join(page['lines']).strip()
            if body:
                out.append(body + '\n')
        markdown = '\n'.join(out).rstrip() + '\n'
        if redact:
            from pyOneNote.redact import redact_secrets
            return redact_secrets(markdown)
        return markdown

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



