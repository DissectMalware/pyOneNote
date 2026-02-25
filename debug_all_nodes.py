import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote import OneNoteParser

parser = OneNoteParser(r'C:\Users\oz303\Oz\MyNotebook\New Section 1.one')

# Get RichText nodes
richtext_nodes = parser.document.get_nodes_by_jcid(['jcidRichTextOENode'])

print(f'Total RichText nodes: {len(richtext_nodes)}\n')

for i, node in enumerate(richtext_nodes):
    if hasattr(node, 'propertySet') and hasattr(node.propertySet, 'body'):
        props = node.propertySet.body.get_properties()
        
        print(f'Node {i}: {list(props.keys())}')
        if 'RichEditTextUnicode' in props:
            val = props['RichEditTextUnicode']
            if isinstance(val, bytes):
                try:
                    decoded = val.decode('utf-16le')
                    print(f'   RichEditTextUnicode: {repr(decoded[:60])}')
                except:
                    print(f'   RichEditTextUnicode: (binary, {len(val)} bytes)')
