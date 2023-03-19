import uuid
import struct
from datetime import datetime, timedelta
import locale

DEBUG = False


class FileNodeListHeader:
    def __init__(self, file):
        self.uintMagic, self.FileNodeListID, self.nFragmentSequence = struct.unpack('<8sII', file.read(16))


class FileNodeList:
    def __init__(self, file, document, file_chunk_reference):
        file.seek(file_chunk_reference.stp)
        self.end = file_chunk_reference.stp + file_chunk_reference.cb
        self.fragments = []

        # FileNodeList can contain one or more FileNodeListFragment
        while True:
            section_end = file_chunk_reference.stp + file_chunk_reference.cb
            fragment = FileNodeListFragment(file, document, section_end)
            self.fragments.append(fragment)
            if fragment.nextFragment.isFcrNil():
                break
            file_chunk_reference = fragment.nextFragment
            file.seek(fragment.nextFragment.stp)


class FileNodeListFragment:
    def __init__(self, file, document, end):
        self.fileNodes = []
        self.fileNodeListHeader = FileNodeListHeader(file)

        # FileNodeListFragment can have one or more FileNode
        while file.tell() + 24 < end:
            node = FileNode(file, document)
            self.fileNodes.append(node)
            if node.file_node_header.file_node_id == 255 or node.file_node_header.file_node_id == 0:
                break

        file.seek(end - 20)
        self.nextFragment = FileChunkReference64x32(file.read(12))
        self.footer, = struct.unpack('<Q', file.read(8))


class FileNodeHeader:
    _FileNodeIDs = {
        0x004: (0x004, 0, "ObjectSpaceManifestRootFND"),
        0x008: (0x008, 2, "ObjectSpaceManifestListReferenceFND"),
        0x00C: (0x00C, 0, "ObjectSpaceManifestListStartFND"),
        0x010: (0x010, 2, "RevisionManifestListReferenceFND"),
        0x014: (0x014, 0, "RevisionManifestListStartFND"),
        0x01B: (0x01B, 0, "RevisionManifestStart4FND"),
        0x01C: (0x01C, 0, "RevisionManifestEndFND"),
        0x01E: (0x01E, 0, "RevisionManifestStart6FND"),
        0x01F: (0x01F, 0, "RevisionManifestStart7FND"),
        0x021: (0x021, 0, "GlobalIdTableStartFNDX"),
        0x022: (0x022, 0, "GlobalIdTableStart2FND"),
        0x024: (0x024, 0, "GlobalIdTableEntryFNDX"),
        0x025: (0x025, 0, "GlobalIdTableEntry2FNDX"),
        0x026: (0x026, 0, "GlobalIdTableEntry3FNDX"),
        0x028: (0x028, 0, "GlobalIdTableEndFNDX"),
        0x02D: (0x02D, 1, "ObjectDeclarationWithRefCountFNDX"),
        0x02E: (0x02E, 1, "ObjectDeclarationWithRefCount2FNDX"),
        0x041: (0x041, 1, "ObjectRevisionWithRefCountFNDX"),
        0x042: (0x042, 1, "ObjectRevisionWithRefCount2FNDX"),
        0x059: (0x059, 0, "RootObjectReference2FNDX"),
        0x05A: (0x05A, 0, "RootObjectReference3FND"),
        0x05C: (0x05C, 0, "RevisionRoleDeclarationFND"),
        0x05D: (0x05D, 0, "RevisionRoleAndContextDeclarationFND"),
        0x072: (0x072, 0, "ObjectDeclarationFileData3RefCountFND"),
        0x073: (0x073, 0, "ObjectDeclarationFileData3LargeRefCountFND"),
        0x07C: (0x07C, 1, "ObjectDataEncryptionKeyV2FNDX"),
        0x084: (0x084, 1, "ObjectInfoDependencyOverridesFND"),
        0x08C: (0x08C, 0, "DataSignatureGroupDefinitionFND"),
        0x090: (0x090, 2, "FileDataStoreListReferenceFND"),
        0x094: (0x094, 1, "FileDataStoreObjectReferenceFND"),
        0x0A4: (0x0A4, 1, "ObjectDeclaration2RefCountFND"),
        0x0A5: (0x0A5, 1, "ObjectDeclaration2LargeRefCountFND"),
        0x0B0: (0x0B0, 2, "ObjectGroupListReferenceFND"),
        0x0B4: (0x0B4, 0, "ObjectGroupStartFND"),
        0x0B8: (0x0B8, 0, "ObjectGroupEndFND"),
        0x0C2: (0x0C2, 1, "HashedChunkDescriptor2FND"),
        0x0C4: (0x0C4, 1, "ReadOnlyObjectDeclaration2RefCountFND"),
        0x0C5: (0x0C5, 1, "ReadOnlyObjectDeclaration2LargeRefCountFND"),
        0x0FF: (0x0FF, -1, "ChunkTerminatorFND")
    }

    def __init__(self, file):
        fileNodeHeader, = struct.unpack('<I', file.read(4))
        self.file_node_id = fileNodeHeader & 0x3ff
        self.file_node_type = "Invalid"
        if self.file_node_id in self._FileNodeIDs:
            self.file_node_type = self._FileNodeIDs[self.file_node_id][2]
        self.size = (fileNodeHeader >> 10) & 0x1fff
        self.stpFormat = (fileNodeHeader >> 23) & 0x3
        self.cbFormat = (fileNodeHeader >> 25) & 0x3
        self.baseType = (fileNodeHeader >> 27) & 0xf
        self.reserved = (fileNodeHeader >> 31)


class FileNode:
    count = 0
    def __init__(self, file, document):
        self.document= document
        self.file_node_header = FileNodeHeader(file)
        if DEBUG:
            print(str(file.tell()) + ' ' + self.file_node_header.file_node_type + ' ' + str(self.file_node_header.baseType))
        self.children = []
        FileNode.count += 1
        if self.file_node_header.file_node_type == "ObjectGroupStartFND":
            self.data = ObjectGroupStartFND(file)
        elif self.file_node_header.file_node_type == "ObjectSpaceManifestListReferenceFND":
            self.data = ObjectSpaceManifestListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "ObjectSpaceManifestListStartFND":
            self.data = ObjectSpaceManifestListStartFND(file)
        elif self.file_node_header.file_node_type == "RevisionManifestListReferenceFND":
            self.data = RevisionManifestListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "RevisionManifestListStartFND":
            self.data = RevisionManifestListStartFND(file)
        elif self.file_node_header.file_node_type == "RevisionManifestStart4FND":
            self.data = RevisionManifestStart4FND(file)
            self.document.cur_revision = self.data.rid
        elif self.file_node_header.file_node_type == "RevisionManifestStart6FND":
            self.data = RevisionManifestStart6FND(file)
            self.document.cur_revision = self.data.rid
        elif self.file_node_header.file_node_type == "ObjectGroupListReferenceFND":
            self.data = ObjectGroupListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "GlobalIdTableEntryFNDX":
            self.data = GlobalIdTableEntryFNDX(file)
            if not self.document.cur_revision in self.document._global_identification_table:
                self.document._global_identification_table[self.document.cur_revision] = {}

            self.document._global_identification_table[self.document.cur_revision][self.data.index] = self.data.guid
        elif self.file_node_header.file_node_type == "DataSignatureGroupDefinitionFND":
            self.data = DataSignatureGroupDefinitionFND(file)
        elif self.file_node_header.file_node_type == "ObjectDeclaration2RefCountFND":
            self.data = ObjectDeclaration2RefCountFND(file, self.document, self.file_node_header)
            current_offset = file.tell()
            if self.data.body.jcid.IsPropertySet:
                file.seek(self.data.ref.stp)
                self.propertySet = ObjectSpaceObjectPropSet(file, document)
            file.seek(current_offset)
        elif self.file_node_header.file_node_type == "ReadOnlyObjectDeclaration2LargeRefCountFND":
            self.data = ReadOnlyObjectDeclaration2LargeRefCountFND(file, self.document, self.file_node_header)
        elif self.file_node_header.file_node_type == "ReadOnlyObjectDeclaration2RefCountFND":
            self.data = ReadOnlyObjectDeclaration2RefCountFND(file, self.document, self.file_node_header)
        elif self.file_node_header.file_node_type == "FileDataStoreListReferenceFND":
            self.data = FileDataStoreListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "FileDataStoreObjectReferenceFND":
            self.data = FileDataStoreObjectReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "ObjectDeclaration2Body":
            self.data = ObjectDeclaration2Body(file, self.document)
        elif self.file_node_header.file_node_type == "ObjectInfoDependencyOverridesFND":
            self.data = ObjectInfoDependencyOverridesFND(file, self.file_node_header, self.document)
        elif self.file_node_header.file_node_type == "RootObjectReference2FNDX":
            self.data = RootObjectReference2FNDX(file, self.document)
        elif self.file_node_header.file_node_type == "RootObjectReference3FND":
            self.data = RootObjectReference3FND(file)
        elif self.file_node_header.file_node_type == "ObjectSpaceManifestRootFND":
            self.data = ObjectSpaceManifestRootFND(file)
        elif self.file_node_header.file_node_type == "ObjectDeclarationFileData3RefCountFND":
            self.data = ObjectDeclarationFileData3RefCountFND(file, self.document)
        elif self.file_node_header.file_node_type == "RevisionRoleDeclarationFND":
            self.data = RevisionRoleDeclarationFND(file)
        elif self.file_node_header.file_node_type == "RevisionRoleAndContextDeclarationFND":
            self.data = RevisionRoleAndContextDeclarationFND(file)
        elif self.file_node_header.file_node_type == "RevisionManifestStart7FND":
            self.data = RevisionManifestStart7FND(file)
            self.document.cur_revision = self.data.base.rid
        elif self.file_node_header.file_node_type in ["RevisionManifestEndFND", "ObjectGroupEndFND"]:
            # no data part
            self.data = None
        else:
            p = 1

        current_offset = file.tell()
        if self.file_node_header.baseType == 2:
            self.children.append(FileNodeList(file, self.document, self.data.ref))
        file.seek(current_offset)


class ExtendedGUID:
    def __init__(self, file):
        self.guid, self.n = struct.unpack('<16sI', file.read(20))
        self.guid = uuid.UUID(bytes_le=self.guid)

    def __repr__(self):
        return 'ExtendedGUID:(guid:{}, n:{})'.format(self.guid, self.n)


class FileNodeChunkReference:
    def __init__(self, file, stpFormat, cbFormat):
        data_size = 0
        stp_compressed = False
        stp_type = ''
        if stpFormat == 0:
            stp_type = 'Q'
            data_size += 8
            self.invalid = 0xffffffffffffffff
        elif stpFormat == 1:
            stp_type = 'I'
            data_size += 4
            self.invalid = 0xffffffff
        elif stpFormat == 2:
            stp_type = 'H'
            data_size += 2
            stp_compressed = True
            self.invalid = 0x7fff8
        elif stpFormat == 3:
            stp_type = 'I'
            data_size += 4
            stp_compressed = True
            self.invalid = 0x7fffffff8

        cb_type = ''
        cb_compressed = False
        if cbFormat == 0:
            cb_type = 'I'
            data_size += 4
        elif cbFormat == 1:
            cb_type = 'Q'
            data_size += 8
        elif cbFormat == 2:
            cb_type = 'B'
            data_size += 1
            cb_compressed = True
        elif cbFormat == 3:
            cb_type = 'H'
            data_size += 2
            cb_compressed = True

        self.stp, self.cb = struct.unpack('<{}{}'.format(stp_type, cb_type), file.read(data_size))
        if stp_compressed:
            self.stp *= 8

        if cb_compressed:
            self.cb *= 8

    def isFcrNil(self):
        res = False
        res = (self.stp & self.invalid) == self.invalid and self.cb == 0
        return res

    def __repr__(self):
        return 'FileChunkReference:(stp:{}, cb:{})'.format(self.stp, self.cb)


class FileChunkReference64x32(FileNodeChunkReference):
    def __init__(self, bytes):
        self.stp, self.cb = struct.unpack('<QI', bytes)
        self.invalid = 0xffffffffffffffff

    def __repr__(self):
        return 'FileChunkReference64x32:(stp:{}, cb:{})'.format(self.stp, self.cb)


class FileChunkReference32(FileNodeChunkReference):
    def __init__(self, bytes):
        self.stp, self.cb = struct.unpack('<II', bytes)
        self.invalid = 0xffffffff

    def __repr__(self):
        return 'FileChunkReference32:(stp:{}, cb:{})'.format(self.stp, self.cb)


class ObjectGroupStartFND:
    def __init__(self, file):
        self.oid = ExtendedGUID(file)


class ObjectSpaceManifestRootFND:
    def __init__(self, file):
        self.gosidRoot = ExtendedGUID(file)


class ObjectSpaceManifestListStartFND:
    def __init__(self, file):
        self.gosid = ExtendedGUID(file)


class ObjectSpaceManifestListReferenceFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.gosid = ExtendedGUID(file)


class RevisionManifestListReferenceFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)


class RevisionManifestListStartFND:
    def __init__(self, file):
        self.gosid = ExtendedGUID(file)
        self.nInstance = file.read(4)


class RevisionManifestStart4FND:
    def __init__(self, file):
        self.rid = ExtendedGUID(file)
        self.ridDependent = ExtendedGUID(file)
        self.timeCreation, self.RevisionRole, self.odcsDefault = struct.unpack('<8sIH', file.read(14))


class RevisionManifestStart6FND:
    def __init__(self, file):
        self.rid = ExtendedGUID(file)
        self.ridDependent = ExtendedGUID(file)
        self.RevisionRole, self.odcsDefault = struct.unpack('<IH', file.read(6))


class ObjectGroupListReferenceFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.ObjectGroupID = ExtendedGUID(file)


class GlobalIdTableEntryFNDX:
    def __init__(self, file):
        self.index, self.guid = struct.unpack('<I16s', file.read(20))
        self.guid = uuid.UUID(bytes_le=self.guid)


class DataSignatureGroupDefinitionFND:
    def __init__(self, file):
        self.DataSignatureGroup = ExtendedGUID(file)


class ObjectDeclaration2LargeRefCountFND:
    def __init__(self, file, document, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.body = ObjectDeclaration2Body(file, document)
        self.cRef, = struct.unpack('<I', file.read(4))


class ObjectDeclaration2RefCountFND:
    def __init__(self, file, document, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.body = ObjectDeclaration2Body(file, document)
        self.cRef, = struct.unpack('<B', file.read(1))


class ReadOnlyObjectDeclaration2LargeRefCountFND:
    def __init__(self, file, document, file_node_header):
        self.base = ObjectDeclaration2LargeRefCountFND(file, document, file_node_header)
        self.md5Hash, = struct.unpack('16s', file.read(16))


class ReadOnlyObjectDeclaration2RefCountFND:
    def __init__(self, file, document, file_node_header):
        self.base = ObjectDeclaration2RefCountFND(file, document, file_node_header)
        self.md5Hash, = struct.unpack('16s', file.read(16))


class ObjectDeclaration2Body:
    def __init__(self, file, document):
        self.oid = CompactID(file, document)
        self.jcid = JCID(file)
        data, = struct.unpack('B', file.read(1))
        self.fHasOidReferences = (data & 0x1) != 0
        self.fHasOsidReferences = (data & 0x2) != 0


class ObjectInfoDependencyOverridesFND:
    def __init__(self, file, file_node_header, document):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        if self.ref.isFcrNil():
            data = ObjectInfoDependencyOverrideData(file, document)


class FileDataStoreListReferenceFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)


class FileDataStoreObjectReferenceFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.guidReference, = struct.unpack('<16s', file.read(16))
        self.guidReference = uuid.UUID(bytes_le=self.guidReference)
        current_offset = file.tell()
        file.seek(self.ref.stp)
        self.fileDataStoreObject = FileDataStoreObject(file, self.ref)
        file.seek(current_offset)

    def __str__(self):
        return 'FileDataStoreObjectReferenceFND: (guidReference:{},fileDataStoreObject:{}'.format(
            self.guidReference,
            str(self.fileDataStoreObject)
        )


class ObjectInfoDependencyOverrideData:
    def __init__(self, file, document):
        self.c8BitOverrides, self.c32BitOverrides, self.crc = struct.unpack('<III', file.read(12))
        self.Overrides1 = []
        for i in range(self.c8BitOverrides):
            self.Overrides1.append(ObjectInfoDependencyOverride8(file, document))
        for i in range(self.c32BitOverrides):
            self.Overrides1.append(ObjectInfoDependencyOverride32(file, document))


class ObjectInfoDependencyOverride8:
    def __init__(self, file, document):
        self.oid = CompactID(file, document)
        self.cRef, = struct.unpack('B', file.read(1))


class ObjectInfoDependencyOverride32:
    def __init__(self, file, document):
        self.oid = CompactID(file, document)
        self.cRef, = struct.unpack('<I', file.read(4))


class RootObjectReference2FNDX:
    def __init__(self, file, document):
        self.oidRoot = CompactID(file, document)
        self.RootRole, = struct.unpack('<I', file.read(4))


class RootObjectReference3FND:
    def __init__(self, file):
        self.oidRoot = ExtendedGUID(file)
        self.RootRole, = struct.unpack('<I', file.read(4))


class ObjectDeclarationFileData3RefCountFND:
    def __init__(self, file, document):
        self.oid = CompactID(file, document)
        self.jcid = JCID(file)
        self.cRef, = struct.unpack('<B', file.read(1))
        self.FileDataReference = StringInStorageBuffer(file)
        self.Extension = StringInStorageBuffer(file)

    def __str__(self):
        return 'ObjectDeclarationFileData3RefCountFND: (jcid:{}, Extension:{}, FileDataReference:{}'.format(
            self.jcid,
            self.Extension,
            self.FileDataReference
        )


class RevisionRoleDeclarationFND:
    def __init__(self, file):
        self.rid = ExtendedGUID(file)
        self.RevisionRole, = struct.unpack('<I', file.read(4))


class RevisionRoleAndContextDeclarationFND:
    def __init__(self, file):
        self.base = RevisionRoleDeclarationFND(file)
        self.gctxid = ExtendedGUID(file)


class RevisionManifestStart7FND:
    def __init__(self, file):
        self.base = RevisionManifestStart6FND(file)
        self.gctxid = ExtendedGUID(file)


class CompactID:
    def __init__(self, file, document):
        data, = struct.unpack('<I', file.read(4))
        self.n = data & 0xff
        self.guidIndex = data >> 8
        self.document = document
        self.current_revision = self.document.cur_revision

    def __str__(self):
        return '<ExtendedGUID> ({}, {})'.format(
        self.document._global_identification_table[self.current_revision][self.guidIndex],
        self.n)

    def __repr__(self):
        return '<ExtendedGUID> ({}, {})'.format(
        self.document._global_identification_table[self.current_revision][self.guidIndex],
        self.n)


class JCID:
    _jcid_name_mapping= {
        0x00120001: "jcidReadOnlyPersistablePropertyContainerForAuthor",
        0x00020001: "jcidPersistablePropertyContainerForTOC",
        0x00020001: "jcidPersistablePropertyContainerForTOCSection",
        0x00060007: "jcidSectionNode",
        0x00060008: "jcidPageSeriesNode",
        0x0006000B: "jcidPageNode",
        0x0006000C: "jcidOutlineNode",
        0x0006000D: "jcidOutlineElementNode",
        0x0006000E: "jcidRichTextOENode",
        0x00060011: "jcidImageNode",
        0x00060012: "jcidNumberListNode",
        0x00060019: "jcidOutlineGroup",
        0x00060022: "jcidTableNode",
        0x00060023: "jcidTableRowNode",
        0x00060024: "jcidTableCellNode",
        0x0006002C: "jcidTitleNode",
        0x00020030: "jcidPageMetaData",
        0x00020031: "jcidSectionMetaData",
        0x00060035: "jcidEmbeddedFileNode",
        0x00060037: "jcidPageManifestNode",
        0x00020038: "jcidConflictPageMetaData",
        0x0006003C: "jcidVersionHistoryContent",
        0x0006003D: "jcidVersionProxy",
        0x00120043: "jcidNoteTagSharedDefinitionContainer",
        0x00020044: "jcidRevisionMetaData",
        0x00020046: "jcidVersionHistoryMetaData",
        0x0012004D: "jcidParagraphStyleObject",
        0x0012004D: "jcidParagraphStyleObjectForText"
    }

    def __init__(self, file):
        self.jcid, = struct.unpack('<I', file.read(4))
        self.index = self.jcid & 0xffff
        self.IsBinary = ((self.jcid >> 16) & 0x1) == 1
        self.IsPropertySet = ((self.jcid >> 17) & 0x1) == 1
        self.IsGraphNode = ((self.jcid >> 18) & 0x1) == 1
        self.IsFileData = ((self.jcid >> 19) & 0x1) == 1
        self.IsReadOnly = ((self.jcid >> 20) & 0x1) == 1

    def get_jcid_name(self):
        return self._jcid_name_mapping[self.jcid] if self.jcid in self._jcid_name_mapping else 'Unknown'

    def __str__(self):
        return self.get_jcid_name()

    def __repr__(self):
        return self.get_jcid_name()


class StringInStorageBuffer:
    def __init__(self, file):
        self.cch, = struct.unpack('<I', file.read(4))
        self.length_in_bytes = self.cch * 2
        self.StringData, = struct.unpack('{}s'.format(self.length_in_bytes), file.read(self.length_in_bytes))
        self.StringData = self.StringData.decode('utf-16')

    def __str__(self):
        return self.StringData


class FileDataStoreObject:
    def __init__(self, file, fileNodeChunkReference):
        self.guidHeader, self.cbLength, self.unused, self.reserved = struct.unpack('<16sQ4s8s', file.read(36))
        self.FileData, = struct.unpack('{}s'.format(self.cbLength), file.read(self.cbLength))
        file.seek(fileNodeChunkReference.stp + fileNodeChunkReference.cb - 16)
        self.guidFooter, = struct.unpack('16s', file.read(16))
        self.guidHeader = uuid.UUID(bytes_le=self.guidHeader)
        self.guidFooter = uuid.UUID(bytes_le=self.guidFooter)

    def __str__(self):
        return self.FileData[:128].hex()


class ObjectSpaceObjectPropSet:
    def __init__(self, file, document):
        self.OIDs = ObjectSpaceObjectStreamOfIDs(file, document)
        self.OSIDs = None
        if not self.OIDs.header.OsidStreamNotPresent:
            self.OSIDs = ObjectSpaceObjectStreamOfIDs(file, document)
        self.ContextIDs = None
        if self.OIDs.header.ExtendedStreamsPresent:
            self.ContextIDs = ObjectSpaceObjectStreamOfIDs(file, document)
        self.body = PropertySet(file, self.OIDs, self.OSIDs, self.ContextIDs, document)


class ObjectSpaceObjectStreamOfIDs:
    def __init__(self, file, document):
        self.header = ObjectSpaceObjectStreamHeader(file)
        self.body = []
        self.head = 0
        for i in range(self.header.Count):
            self.body.append(CompactID(file, document))

    def read(self):
        res = None
        if self.head < len(self.body):
            res = self.body[self.head]
        return res

    def reset(self):
        self.head = 0


class ObjectSpaceObjectStreamHeader:
    def __init__(self, file):
        data, = struct.unpack('<I', file.read(4))
        self.Count = data & 0xffffff
        self.ExtendedStreamsPresent = (data >> 30) & 1 == 1
        self.OsidStreamNotPresent = (data >> 31) & 1 == 1


class PropertySet:
    def __init__(self, file, OIDs, OSIDs, ContextIDs, document):
        self.current = file.tell()
        self.cProperties, = struct.unpack('<H', file.read(2))
        self.rgPrids = []
        self.indent = ''
        self.document = document
        self.current_revision = document.cur_revision
        self._formated_properties = None
        for i in range(self.cProperties):
            self.rgPrids.append(PropertyID(file))

        self.rgData = []
        for i in range(self.cProperties):
            type = self.rgPrids[i].type
            if type == 0x1:
                self.rgData.append(None)
            elif type == 0x2:
                self.rgData.append(self.rgPrids[i].boolValue)
            elif type == 0x3:
                self.rgData.append(struct.unpack('c', file.read(1))[0])
            elif type == 0x4:
                self.rgData.append(struct.unpack('2s', file.read(2))[0])
            elif type == 0x5:
                self.rgData.append(struct.unpack('4s', file.read(4))[0])
            elif type == 0x6:
                self.rgData.append(struct.unpack('8s', file.read(8))[0])
            elif type == 0x7:
                self.rgData.append(PrtFourBytesOfLengthFollowedByData(file, self))
            elif type == 0x8 or type == 0x09:
                count = 1
                if type == 0x09:
                    count, = struct.unpack('<I', file.read(4))
                self.rgData.append(self.get_compact_ids(OIDs, count))
            elif type == 0xA or type == 0x0B:
                count = 1
                if type == 0x0B:
                    count, = struct.unpack('<I', file.read(4))
                self.rgData.append(self.get_compact_ids(OSIDs, count))
            elif type == 0xC or type == 0x0D:
                count = 1
                if type == 0x0D:
                    count, = struct.unpack('<I', file.read(4))
                self.rgData.append(self.get_compact_ids(ContextIDs, count))
            elif type == 0x10:
                raise NotImplementedError('ArrayOfPropertyValues is not implement')
            elif type == 0x11:
                self.rgData.append(PropertySet(file))
            else:
                raise ValueError('rgPrids[i].type is not valid')

    @staticmethod
    def get_compact_ids(stream_of_context_ids, count):
        data = []
        for i in range(count):
            data.append(stream_of_context_ids.read())
        return data


    def get_properties(self):
        if self._formated_properties is not None :
            return self._formated_properties

        self._formated_properties = {}
        for i in range(self.cProperties):
            propertyName = str(self.rgPrids[i])
            if propertyName != 'Unknown':
                propertyVal = ''
                if isinstance(self.rgData[i], PrtFourBytesOfLengthFollowedByData):
                    if 'guid' in propertyName.lower():
                        propertyVal = uuid.UUID(bytes_le=self.rgData[i].Data)
                    else:
                        try:
                            propertyVal = self.rgData[i].Data.decode('utf-16')
                        except:
                            propertyVal = self.rgData[i].Data.hex()
                else:
                    property_name_lower =  propertyName.lower()
                    if 'time' in property_name_lower:
                        if len(self.rgData[i]) == 8:
                            timestamp_in_nano, = struct.unpack('<Q', self.rgData[i])
                            propertyVal = PropertySet.parse_filetime(timestamp_in_nano)
                        else:
                            timestamp_in_sec, = struct.unpack('<I', self.rgData[i])
                            propertyVal = PropertySet.time32_to_datetime(timestamp_in_sec)
                    elif 'height' in property_name_lower or \
                            'width' in property_name_lower or \
                            'offset' in property_name_lower or \
                            'margin' in property_name_lower:
                        size, = struct.unpack('<f', self.rgData[i])
                        propertyVal = PropertySet.half_inch_size_to_pixels(size)
                    elif 'langid' in property_name_lower:
                        lcid, =struct.unpack('<H', self.rgData[i])
                        propertyVal = '{}({})'.format(PropertySet.lcid_to_string(lcid), lcid)
                    elif 'languageid' in property_name_lower:
                        lcid, =struct.unpack('<I', self.rgData[i])
                        propertyVal = '{}({})'.format(PropertySet.lcid_to_string(lcid), lcid)
                    else:
                        if isinstance(self.rgData[i], CompactID):
                            propertyVal = '{}:{}'.format(str(self.document._global_identification_table[self.current_revision][self.rgData[i].guidIndex]), str(self.rgData[i].n))
                        else:
                            propertyVal = str(self.rgData[i])
                self._formated_properties[propertyName] = str(propertyVal)
        return self._formated_properties


    def __str__(self):
        result = ''
        for propertyName, propertyVal in self.get_properties().items():
            result += '{}{}: {}\n'.format(self.indent, propertyName, propertyVal)
        return result

    [staticmethod]
    def half_inch_size_to_pixels(picture_width, dpi=96):
        # Number of pixels per half-inch
        pixels_per_half_inch = dpi / 2

        # Calculate the number of pixels
        pixels = picture_width * pixels_per_half_inch

        return int(pixels)

    [staticmethod]
    def time32_to_datetime(time32):
        # Define the starting time (12:00 A.M., January 1, 1980, UTC)
        start = datetime(1980, 1, 1, 0, 0, 0)

        # Calculate the number of seconds represented by the Time32 value
        seconds = time32

        # Calculate the final datetime by adding the number of seconds to the starting time
        dt = start + timedelta(seconds=seconds)

        return dt


    [staticmethod]
    def parse_filetime(filetime):
        # Define the number of 100-nanosecond intervals in 1 second
        intervals_per_second = 10 ** 7

        # Define the number of seconds between January 1, 1601 and January 1, 1970
        seconds_between_epochs = 11644473600

        # Calculate the number of seconds represented by the FILETIME value
        seconds = filetime / intervals_per_second

        # Calculate the number of seconds that have elapsed since January 1, 1970
        seconds_since_epoch = seconds - seconds_between_epochs

        # Convert the number of seconds to a datetime object
        dt = datetime(1970, 1, 1) + timedelta(seconds=seconds_since_epoch)

        return dt

    [staticmethod]
    def lcid_to_string(lcid):
        return locale.windows_locale.get(lcid, 'Unknown LCID')


class PrtFourBytesOfLengthFollowedByData:
    def __init__(self, file, propertySet):
        self.cb, = struct.unpack('<I', file.read(4))
        self.Data, = struct.unpack('{}s'.format(self.cb), file.read(self.cb))

    def __str__(self):
        return self.Data.hex()


class PropertyID:
    _property_id_name_mapping = {
        0x08001C00: "LayoutTightLayout",
        0x14001C01: "PageWidth",
        0x14001C02: "PageHeight",
        0x0C001C03: "OutlineElementChildLevel",
        0x08001C04: "Bold",
        0x08001C05: "Italic",
        0x08001C06: "Underline",
        0x08001C07: "Strikethrough",
        0x08001C08: "Superscript",
        0x08001C09: "Subscript",
        0x1C001C0A: "Font",
        0x10001C0B: "FontSize",
        0x14001C0C: "FontColor",
        0x14001C0D: "Highlight",
        0x1C001C12: "RgOutlineIndentDistance",
        0x0C001C13: "BodyTextAlignment",
        0x14001C14: "OffsetFromParentHoriz",
        0x14001C15: "OffsetFromParentVert",
        0x1C001C1A: "NumberListFormat",
        0x14001C1B: "LayoutMaxWidth",
        0x14001C1C: "LayoutMaxHeight",
        0x24001C1F: "ContentChildNodesOfOutlineElement",
        0x24001C1F: "ContentChildNodesOfPageManifest",
        0x24001C20: "ElementChildNodesOfSection",
        0x24001C20: "ElementChildNodesOfPage",
        0x24001C20: "ElementChildNodesOfTitle",
        0x24001C20: "ElementChildNodesOfOutline",
        0x24001C20: "ElementChildNodesOfOutlineElement",
        0x24001C20: "ElementChildNodesOfTable",
        0x24001C20: "ElementChildNodesOfTableRow",
        0x24001C20: "ElementChildNodesOfTableCell",
        0x24001C20: "ElementChildNodesOfVersionHistory",
        0x08001E1E: "EnableHistory",
        0x1C001C22: "RichEditTextUnicode",
        0x24001C26: "ListNodes",
        0x1C001C30: "NotebookManagementEntityGuid",
        0x08001C34: "OutlineElementRTL",
        0x14001C3B: "LanguageID",
        0x14001C3E: "LayoutAlignmentInParent",
        0x20001C3F: "PictureContainer",
        0x14001C4C: "PageMarginTop",
        0x14001C4D: "PageMarginBottom",
        0x14001C4E: "PageMarginLeft",
        0x14001C4F: "PageMarginRight",
        0x1C001C52: "ListFont",
        0x18001C65: "TopologyCreationTimeStamp",
        0x14001C84: "LayoutAlignmentSelf",
        0x08001C87: "IsTitleTime",
        0x08001C88: "IsBoilerText",
        0x14001C8B: "PageSize",
        0x08001C8E: "PortraitPage",
        0x08001C91: "EnforceOutlineStructure",
        0x08001C92: "EditRootRTL",
        0x08001CB2: "CannotBeSelected",
        0x08001CB4: "IsTitleText",
        0x08001CB5: "IsTitleDate",
        0x14001CB7: "ListRestart",
        0x08001CBD: "IsLayoutSizeSetByUser",
        0x14001CCB: "ListSpacingMu",
        0x14001CDB: "LayoutOutlineReservedWidth",
        0x08001CDC: "LayoutResolveChildCollisions",
        0x08001CDE: "IsReadOnly",
        0x14001CEC: "LayoutMinimumOutlineWidth",
        0x14001CF1: "LayoutCollisionPriority",
        0x1C001CF3: "CachedTitleString",
        0x08001CF9: "DescendantsCannotBeMoved",
        0x10001CFE: "RichEditTextLangID",
        0x08001CFF: "LayoutTightAlignment",
        0x0C001D01: "Charset",
        0x14001D09: "CreationTimeStamp",
        0x08001D0C: "Deletable",
        0x10001D0E: "ListMSAAIndex",
        0x08001D13: "IsBackground",
        0x14001D24: "IRecordMedia",
        0x1C001D3C: "CachedTitleStringFromPage",
        0x14001D57: "RowCount",
        0x14001D58: "ColumnCount",
        0x08001D5E: "TableBordersVisible",
        0x24001D5F: "StructureElementChildNodes",
        0x2C001D63: "ChildGraphSpaceElementNodes",
        0x1C001D66: "TableColumnWidths",
        0x1C001D75: "Author",
        0x18001D77: "LastModifiedTimeStamp",
        0x20001D78: "AuthorOriginal",
        0x20001D79: "AuthorMostRecent",
        0x14001D7A: "LastModifiedTime",
        0x08001D7C: "IsConflictPage",
        0x1C001D7D: "TableColumnsLocked",
        0x14001D82: "SchemaRevisionInOrderToRead",
        0x08001D96: "IsConflictObjectForRender",
        0x20001D9B: "EmbeddedFileContainer",
        0x1C001D9C: "EmbeddedFileName",
        0x1C001D9D: "SourceFilepath",
        0x1C001D9E: "ConflictingUserName",
        0x1C001DD7: "ImageFilename",
        0x08001DDB: "IsConflictObjectForSelection",
        0x14001DFF: "PageLevel",
        0x1C001E12: "TextRunIndex",
        0x24001E13: "TextRunFormatting",
        0x08001E14: "Hyperlink",
        0x0C001E15: "UnderlineType",
        0x08001E16: "Hidden",
        0x08001E19: "HyperlinkProtected",
        0x08001E22: "TextRunIsEmbeddedObject",
        0x14001e26: "CellShadingColor",
        0x1C001E58: "ImageAltText",
        0x08003401: "MathFormatting",
        0x2000342C: "ParagraphStyle",
        0x1400342E: "ParagraphSpaceBefore",
        0x1400342F: "ParagraphSpaceAfter",
        0x14003430: "ParagraphLineSpacingExact",
        0x24003442: "MetaDataObjectsAboveGraphSpace",
        0x24003458: "TextRunDataObject",
        0x40003499: "TextRunData",
        0x1C00345A: "ParagraphStyleId",
        0x08003462: "HasVersionPages",
        0x10003463: "ActionItemType",
        0x10003464: "NoteTagShape",
        0x14003465: "NoteTagHighlightColor",
        0x14003466: "NoteTagTextColor",
        0x14003467: "NoteTagPropertyStatus",
        0x1C003468: "NoteTagLabel",
        0x1400346E: "NoteTagCreated",
        0x1400346F: "NoteTagCompleted",
        0x20003488: "NoteTagDefinitionOid",
        0x04003489: "NoteTagStates",
        0x10003470: "ActionItemStatus",
        0x0C003473: "ActionItemSchemaVersion",
        0x08003476: "ReadingOrderRTL",
        0x0C003477: "ParagraphAlignment",
        0x3400347B: "VersionHistoryGraphSpaceContextNodes",
        0x14003480: "DisplayedPageNumber",
        0x1C00349B: "SectionDisplayName",
        0x1C00348A: "NextStyle",
        0x200034C8: "WebPictureContainer14",
        0x140034CB: "ImageUploadState",
        0x1C003498: "TextExtendedAscii",
        0x140034CD: "PictureWidth",
        0x140034CE: "PictureHeight",
        0x14001D0F: "PageMarginOriginX",
        0x14001D10: "PageMarginOriginY",
        0x1C001E20: "WzHyperlinkUrl",
        0x1400346B: "TaskTagDueDate",
        0x1C001DE9: "IsDeletedGraphSpaceContent",
    }

    def __init__(self, file):
        self.value, = struct.unpack('<I', file.read(4))
        self.id = self.value & 0x3ffffff
        self.type = (self.value >> 26) & 0x1f
        self.boolValue = (self.value >> 31) & 1 == 1

    def get_property_name(self):
        return self._property_id_name_mapping[self.value] if self.value in self._property_id_name_mapping else 'Unknown'

    def __str__(self):
        return self.get_property_name()
