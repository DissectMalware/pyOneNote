import uuid
import struct


class FileNodeListHeader:
    def __init__(self, file):
        self.uintMagic, self.FileNodeListID, self.nFragmentSequence  = struct.unpack('<8sII', file.read(16))


class FileNodeList:
    def __init__(self, file, file_chunck_reference):
        file.seek(file_chunck_reference.stp)
        self.end = file_chunck_reference.stp + file_chunck_reference.cb
        self.fileNodeListHeader = FileNodeListHeader(file)
        self.fragment = FileNodeListFragment(file, self.end)



class FileNodeListFragment:
    def __init__(self, file, end):
        while file.tell() + 24 < end:
            self.fileNode = FileNode(file)


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

        current_offset = file.tell()

        if self.file_node_header.baseType == 2:
            FileNodeList(file, self.data.ref)

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
        elif stpFormat == 1:
            stp_type = 'I'
            data_size += 4
        elif stpFormat == 2:
            stp_type = 'H'
            data_size += 2
            stp_compressed = True
        elif stpFormat == 3:
            stp_type = 'I'
            data_size += 4
            stp_compressed = True

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

    def __repr__(self):
        return 'FileChunkReference:(stp:{}, cb:{})'.format(self.stp, self.cb)


class FileChunkReference64x32:
    def __init__(self, bytes):
        self.stp, self.cb = struct.unpack('<QI', bytes)

    def __repr__(self):
        return 'FileChunkReference64x32:(stp:{}, cb:{})'.format(self.stp, self.cb)


class FileChunkReference32:
    def __init__(self, bytes):
        self.stp, self.cb = struct.unpack('<II', bytes)

    def __repr__(self):
        return 'FileChunkReference32:(stp:{}, cb:{})'.format(self.stp, self.cb)


class ObjectGroupStartFND:
    def __init__(self, file):
        self.oid = ExtendedGUID(file)


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

