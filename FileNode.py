import uuid
import struct


class FileNodeListHeader:
    def __init__(self, file):
        self.uintMagic, self.FileNodeListID, self.nFragmentSequence = struct.unpack('<8sII', file.read(16))


class FileNodeList:
    def __init__(self, file, file_chunk_reference):
        file.seek(file_chunk_reference.stp)
        self.end = file_chunk_reference.stp + file_chunk_reference.cb
        self.fragments = []

        # FileNodeList can contain one or more FileNodeListFragment
        while True:
            section_end = file_chunk_reference.stp + file_chunk_reference.cb
            fragment = FileNodeListFragment(file, section_end)
            self.fragments.append(fragment)
            if fragment.nextFragment.isFcrNil():
                break
            file_chunk_reference = fragment.nextFragment
            file.seek(fragment.nextFragment.stp)


class FileNodeListFragment:
    def __init__(self, file, end):
        self.fileNodes = []
        self.fileNodeListHeader = FileNodeListHeader(file)

        # FileNodeListFragment can have one or more FileNode
        while file.tell() + 24 < end:
            node = FileNode(file)
            self.fileNodes.append(node)
            if node.file_node_header.file_node_id == 255 or node.file_node_header.file_node_id == 0:
                break

        file.seek(end-20)
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
    def __init__(self, file):
        self.file_node_header = FileNodeHeader(file)
        self.children = []

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
        elif self.file_node_header.file_node_type == "RevisionManifestStart6FND":
            self.data = RevisionManifestStart6FND(file)
        elif self.file_node_header.file_node_type == "ObjectGroupListReferenceFND":
            self.data = ObjectGroupListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "GlobalIdTableEntryFNDX":
            self.data = GlobalIdTableEntryFNDX(file)
        elif self.file_node_header.file_node_type == "DataSignatureGroupDefinitionFND":
            self.data = DataSignatureGroupDefinitionFND(file)
        elif self.file_node_header.file_node_type == "ObjectDeclaration2RefCountFND":
            self.data = ObjectDeclaration2RefCountFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "ReadOnlyObjectDeclaration2RefCountFND":
            self.data = ReadOnlyObjectDeclaration2RefCountFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "FileDataStoreListReferenceFND":
            self.data = FileDataStoreListReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "FileDataStoreObjectReferenceFND":
            self.data = FileDataStoreObjectReferenceFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "ObjectDeclaration2Body":
            self.data = ObjectDeclaration2Body(file)
        elif self.file_node_header.file_node_type == "ObjectInfoDependencyOverridesFND":
            self.data = ObjectInfoDependencyOverridesFND(file, self.file_node_header)
        elif self.file_node_header.file_node_type == "RootObjectReference3FND":
            self.data = RootObjectReference3FND(file)
        elif self.file_node_header.file_node_type == "ObjectSpaceManifestRootFND":
            self.data = ObjectSpaceManifestRootFND(file)
        elif self.file_node_header.file_node_type == "ObjectDeclarationFileData3RefCountFND":
            self.data = ObjectDeclarationFileData3RefCountFND(file)
        elif self.file_node_header.file_node_type in ["RevisionManifestEndFND", "ObjectGroupEndFND"]:
            # no data part
            self.data = None
        else:
            p = 1

        current_offset = file.tell()

        if self.file_node_header.baseType == 2:
            self.children.append(FileNodeList(file, self.data.ref))

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


class ObjectDeclaration2RefCountFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        self.body = ObjectDeclaration2Body(file)
        self.cRef, = struct.unpack('<B', file.read(1))


class ReadOnlyObjectDeclaration2RefCountFND:
    def __init__(self, file, file_node_header):
        self.base = ObjectDeclaration2RefCountFND(file, file_node_header)
        self.md5Hash = struct.unpack('16s', file.read(16))


class ObjectDeclaration2Body:
    def __init__(self, file):
        self.oid = CompactID(file)
        self.jcid = JCID(file)
        data, = struct.unpack('B', file.read(1))
        self.fHasOidReferences = (data & 0x1) != 0
        self.fHasOsidReferences = (data & 0x2) != 0


class ObjectInfoDependencyOverridesFND:
    def __init__(self, file, file_node_header):
        self.ref = FileNodeChunkReference(file, file_node_header.stpFormat, file_node_header.cbFormat)
        if self.ref.isFcrNil():
            data = ObjectInfoDependencyOverrideData(file)


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


class ObjectInfoDependencyOverrideData:
    def __init__(self, file):
        self.c8BitOverrides, self.c32BitOverrides, self.crc = struct.unpack('<III', file.read(12))
        self.Overrides1 = []
        for i in range(self.c8BitOverrides):
            self.Overrides1.append(ObjectInfoDependencyOverride8(file))
        for i in range(self.c32BitOverrides):
            self.Overrides1.append(ObjectInfoDependencyOverride32(file))


class ObjectInfoDependencyOverride8:
    def __init__(self, file):
        self.oid = CompactID(file)
        self.cRef, = struct.unpack('B', file.read(1))


class ObjectInfoDependencyOverride32:
    def __init__(self, file):
        self.oid = CompactID(file)
        self.cRef, = struct.unpack('<I', file.read(4))


class RootObjectReference3FND:
    def __init__(self, file):
        self.oidRoot = ExtendedGUID(file)
        self.RootRole, = struct.unpack('<I', file.read(4))


class ObjectDeclarationFileData3RefCountFND:
    def __init__(self, file):
        self.oid = CompactID(file)
        self.jcid = JCID(file)
        self.cRef, = struct.unpack('<B', file.read(1))
        self.FileDataReference = StringInStorageBuffer(file)
        self.Extension = StringInStorageBuffer(file)


class CompactID:
    def __init__(self, file):
        data, = struct.unpack('<I', file.read(4))
        self.n = data & 0xff
        self.guidIndex = data >> 8


class JCID:
    def __init__(self, file):
        self.jcid, = struct.unpack('<I', file.read(4))
        self.index = self.jcid & 0xffff
        self.IsBinary = ((self.jcid >> 16) & 0x1) == 1
        self.IsPropertySet = ((self.jcid >> 17) & 0x1) == 1
        self.IsGraphNode = ((self.jcid >> 18) & 0x1) == 1
        self.IsFileData = ((self.jcid >> 19) & 0x1) == 1
        self.IsReadOnly = ((self.jcid >> 20) & 0x1) == 1


class StringInStorageBuffer:
    def __init__(self, file):
        self.cch, = struct.unpack('<I', file.read(4))
        self.length_in_bytes = self.cch*2
        self.StringData, = struct.unpack('{}s'.format(self.length_in_bytes), file.read(self.length_in_bytes))
        self.StringData = self.StringData.decode('utf-16')


class FileDataStoreObject:
    def __init__(self, file, fileNodeChunkReference):
        self.guidHeader, self.cbLength, self.unused, self.reserved = struct.unpack('<16sQ4s8s', file.read(36))
        self.FileData, = struct.unpack('{}s'.format(self.cbLength), file.read(self.cbLength))
        file.seek(fileNodeChunkReference.stp + fileNodeChunkReference.cb - 16)
        self.guidFooter, = struct.unpack('16s', file.read(16))
        self.guidHeader = uuid.UUID(bytes_le=self.guidHeader)
        self.guidFooter = uuid.UUID(bytes_le=self.guidFooter)