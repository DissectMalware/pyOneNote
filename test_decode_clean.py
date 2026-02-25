import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote import OneNoteParser

parser = OneNoteParser(r'C:\Users\oz303\Oz\MyNotebook\New Section 1.one')
richtext_nodes = parser.document.get_nodes_by_jcid(['jcidRichTextOENode'])

print(f'Processing {len(richtext_nodes)} RichText nodes...\n')

from pyOneNote.exporter import _clean_text_content

for i, rt_node in enumerate(richtext_nodes):
    if hasattr(rt_node, 'propertySet') and hasattr(rt_node.propertySet, 'body'):
        props = rt_node.propertySet.body.get_properties()
        
        if 'RichEditTextUnicode' not in props:
            continue
        
        text = props['RichEditTextUnicode']
        
        # Debug the conversion
        if isinstance(text, bytes):
            try:
                text_decoded = text.decode('utf-16le')
            except:
                text_decoded = "(decode failed)"
        else:
            text_decoded = text
        
        # Now clean it
        cleaned = _clean_text_content(str(text_decoded))
        
        print(f'Node {i}:')
        print(f'  Raw type: {type(text).__name__}')
        print(f'  After decode: {repr(text_decoded[:60])}')
        print(f'  After clean: {repr(cleaned[:60] if cleaned else "(EMPTY)")}')
        print()
