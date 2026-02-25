import sys
import json

# Force reload
for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote.models import OneNoteNotebook

notebook = OneNoteNotebook(path=r'C:\Users\oz303\Oz\MyNotebook')

print('✓ Notebook parsed!')
print(f'  Sections: {len(notebook.sections)}')
print(f'  Pages: {sum(len(s.pages) for s in notebook.sections)}')
print(f'  Section Groups: {len(notebook.section_groups)}')

print(f'\n--- Page Samples ---')
for i, section in enumerate(notebook.sections):
    for j, page in enumerate(section.pages[:5]):
        print(f'\nPage {j+1}:')
        print(f'  Title: "{page.title}"')
        print(f'  Content preview: "{page.content[:100]}"')
        has_null = chr(0) in page.content
        has_escape = '\\x' in repr(page.content)
        print(f'  Clean text: {not has_null and not has_escape}')
