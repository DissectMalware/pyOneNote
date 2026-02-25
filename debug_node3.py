import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote import OneNoteParser

parser = OneNoteParser(r'C:\Users\oz303\Oz\MyNotebook\New Section 1.one')

# Get RichText nodes
richtext_nodes = parser.document.get_nodes_by_jcid(['jcidRichTextOENode'])

# Check node 3 (the problematic one)
if len(richtext_nodes) > 2:
    node = richtext_nodes[2]
    if hasattr(node, 'propertySet') and hasattr(node.propertySet, 'body'):
        props = node.propertySet.body.get_properties()
        
        print('Node 3 properties:')
        for key in ['RichEditTextUnicode', 'CachedTitleString']:
            if key in props:
                val = props[key]
                print(f'\n{key}:')
                print(f'  Type: {type(val)}')
                if isinstance(val, bytes):
                    print(f'  Raw bytes: {val[:100]}')
                    try:
                        decoded = val.decode('utf-16le')
                        print(f'  Decoded: {repr(decoded[:100])}')
                    except Exception as e:
                        print(f'  Decode error: {e}')
                else:
                    print(f'  Value: {repr(val[:200])}')
