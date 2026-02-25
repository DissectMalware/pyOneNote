import sys

for key in list(sys.modules.keys()):
    if key.startswith('pyOneNote'):
        del sys.modules[key]

from pyOneNote.exporter import _clean_text_content

test_texts = [
    'יום\xa0רביעי 25 פברואר 2026\x00',
    'זאת חוברת לדוגמא\x00',
    'הנה - כתוב פה טקסט. איזה יופי!\x00',
]

for text in test_texts:
    cleaned = _clean_text_content(text)
    print(f'Input:  {repr(text[:60])}')
    print(f'Output: {repr(cleaned[:60])}')
    print(f'Empty:  {not cleaned}')
    print()
