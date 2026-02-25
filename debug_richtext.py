import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote import OneNoteParser

parser = OneNoteParser(r'C:\Users\oz303\Oz\MyNotebook\New Section 1.one')
richtext_nodes = parser.document.get_nodes_by_jcid(['jcidRichTextOENode'])

# Check nodes with RichEditTextUnicode
count = 0
for i, node in enumerate(richtext_nodes):
    if hasattr(node, 'propertySet') and hasattr(node.propertySet, 'body'):
        props = node.propertySet.body.get_properties()
        if 'RichEditTextUnicode' in props:
            count += 1
            text = props['RichEditTextUnicode']
            if isinstance(text, bytes):
                try:
                    decoded = text.decode('utf-16le')
                except:
                    decoded = "(decode failed)"
            else:
                decoded = text
            print(f'Node {i}: {repr(decoded[:80])}')

print(f'\nTotal nodes with RichEditTextUnicode: {count}')
