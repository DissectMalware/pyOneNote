"""Regression test for the FileNode terminator / unknown-node crash.

Before the fix, ``FileNode.__init__`` dereferenced ``self.data.ref`` for any
node whose header ``baseType == 2`` (a reference node), but the dispatch
chain's final ``else`` branch left ``self.data`` unset for unrecognised or
terminator node IDs. A single 4-byte FileNode header with an unknown id and
``baseType == 2`` triggered:

    AttributeError: 'FileNode' object has no attribute 'data'

The real-world trigger is a FileNodeListFragment terminator (file_node_id 0
with non-zero upper bits, seen in large / heavily-revised .one sections): the
fragment loop breaks on id 0/255, but only *after* the node is constructed,
so the crash beats the guard. No sample .one file is needed to reproduce it.
"""

import struct
from io import BytesIO

from pyOneNote.FileNode import FileNode


class _Doc:
    """Minimal document stand-in; unused on this code path."""

    cur_revision = None
    _global_identification_table: dict = {}


def _reference_node_with_unknown_id() -> bytes:
    """4-byte FileNode header: file_node_id=0 (Invalid), baseType=2.

        bits  0-9  file_node_id = 0   (not in _FileNodeIDs -> "Invalid")
        bits 10-22 size         = 4
        bits 27-30 baseType     = 2   (reference node -> would recurse)
    """
    header = (0) | (4 << 10) | (2 << 27)  # 0x10001000
    return struct.pack("<I", header)


def test_unknown_reference_node_does_not_crash():
    node = FileNode(BytesIO(_reference_node_with_unknown_id()), _Doc())
    # No child list is read; the node is simply empty.
    assert node.data is None
    assert node.children == []
