import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote import OneNoteParser
from pyOneNote.exporter import _build_tree_structure

parser = OneNoteParser(r'C:\Users\oz303\Oz\MyNotebook\New Section 1.one')

sections_dict, section_groups, all_pages, section_to_pages_map = _build_tree_structure(parser.document)

print(f'Sections: {len(sections_dict)}')
print(f'Pages: {len(all_pages)}')
print(f'Section groups: {len(section_groups)}')

print(f'\nPages:')
for i, page in enumerate(all_pages[:10]):
    print(f'{i+1}. {page.title[:60]}')
