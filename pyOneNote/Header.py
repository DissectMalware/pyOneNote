import struct
import uuid
import json
from FileNode import *


class Header:
    ONE_UUID = uuid.UUID('{7B5C52E4-D88C-4DA7-AEB1-5378D02996D3}')
    ONETOC2_UUID = uuid.UUID('{43FF2FA1-EFD9-4C76-9EE2-10EA5722765F}')
    GUID_FILE_FORMAT_UUID = uuid.UUID('{109ADD3F-911B-49F5-A5D0-1791EDC8AED8}')
    HEADER_FORMAT = "<16s16s16s16sIIII8s8sIIQ8sIBBBB16sI12s12s12s12sQQ16sQ16sI12s12sIIII728s"

    guidFileType = None
    guidFile = None
    guidLegacyFileVersion = None
    guidFileFormat = None
    ffvLastCodeThatWroteToThisFile = None
    ffvOldestCodeThatHasWrittenToThisFile = None
    ffvNewestCodeThatHasWrittenToThisFile = None
    ffvOldestCodeThatMayReadThisFile = None
    fcrLegacyFreeChunkList = None
    fcrLegacyTransactionLog = None
    cTransactionsInLog = None
    cbLegacyExpectedFileLength = None
    rgbPlaceholder = None
    fcrLegacyFileNodeListRoot = None
    cbLegacyFreeSpaceInFreeChunkList = None
    fNeedsDefrag = None
    fRepairedFile = None
    fNeedsGarbageCollect = None
    fHasNoEmbeddedFileObjects = None
    guidAncestor = None
    crcName = None
    fcrHashedChunkList = None
    fcrTransactionLog = None
    fcrFileNodeListRoot = None
    fcrFreeChunkList = None
    cbExpectedFileLength = None
    cbFreeSpaceInFreeChunkList = None
    guidFileVersion = None
    nFileVersionGeneration = None
    guidDenyReadFileVersion = None
    grfDebugLogFlags = None
    fcrDebugLog = None
    fcrAllocVerificationFreeChunkList = None
    bnCreated = None
    bnLastWroteToThisFile = None
    bnOldestWritten = None
    bnNewestWritten = None
    rgbReserved = None

    def __init__(self, file):
        self.guidFileType, \
        self.guidFile, \
        self.guidLegacyFileVersion, \
        self.guidFileFormat, \
        self.ffvLastCodeThatWroteToThisFile, \
        self.ffvOldestCodeThatHasWrittenToThisFile, \
        self.ffvNewestCodeThatHasWrittenToThisFile, \
        self.ffvOldestCodeThatMayReadThisFile, \
        self.fcrLegacyFreeChunkList, \
        self.fcrLegacyTransactionLog, \
        self.cTransactionsInLog, \
        self.cbLegacyExpectedFileLength, \
        self.rgbPlaceholder, \
        self.fcrLegacyFileNodeListRoot, \
        self.cbLegacyFreeSpaceInFreeChunkList, \
        self.fNeedsDefrag, \
        self.fRepairedFile, \
        self.fNeedsGarbageCollect, \
        self.fHasNoEmbeddedFileObjects, \
        self.guidAncestor, \
        self.crcName, \
        self.fcrHashedChunkList, \
        self.fcrTransactionLog, \
        self.fcrFileNodeListRoot, \
        self.fcrFreeChunkList, \
        self.cbExpectedFileLength, \
        self.cbFreeSpaceInFreeChunkList, \
        self.guidFileVersion, \
        self.nFileVersionGeneration, \
        self.guidDenyReadFileVersion, \
        self.grfDebugLogFlags, \
        self.fcrDebugLog, \
        self.fcrAllocVerificationFreeChunkList, \
        self.bnCreated, \
        self.bnLastWroteToThisFile, \
        self.bnOldestWritten, \
        self.bnNewestWritten, \
        self.rgbReserved, = struct.unpack(self.HEADER_FORMAT, file.read(1024))

        self.guidFileType = uuid.UUID(bytes_le=self.guidFileType)
        self.guidFile = uuid.UUID(bytes_le=self.guidFile)
        self.guidLegacyFileVersion = uuid.UUID(bytes_le=self.guidLegacyFileVersion)
        self.guidFileFormat = uuid.UUID(bytes_le=self.guidFileFormat)
        self.guidAncestor = uuid.UUID(bytes_le=self.guidAncestor)
        self.guidFileVersion = uuid.UUID(bytes_le=self.guidFileVersion )
        self.guidDenyReadFileVersion = uuid.UUID(bytes_le=self.guidDenyReadFileVersion)

        self.fcrHashedChunkList = FileChunkReference64x32(self.fcrHashedChunkList)
        self.fcrTransactionLog = FileChunkReference64x32(self.fcrTransactionLog)
        self.fcrFileNodeListRoot = FileChunkReference64x32(self.fcrFileNodeListRoot)
        self.fcrFreeChunkList = FileChunkReference64x32(self.fcrFreeChunkList)
        self.fcrDebugLog = FileChunkReference64x32(self.fcrDebugLog)
        self.fcrAllocVerificationFreeChunkList = FileChunkReference64x32(
            self.fcrAllocVerificationFreeChunkList)

        self.fcrLegacyFreeChunkList = FileChunkReference32(self.fcrLegacyFreeChunkList)
        self.fcrLegacyTransactionLog = FileChunkReference32(self.fcrLegacyTransactionLog)
        self.fcrLegacyFileNodeListRoot = FileChunkReference32(self.fcrLegacyFileNodeListRoot)


    def convert_to_dictionary(self):
        res = {}
        for key, item in self.__dict__.items():
            if not key.startswith('_') and not key == 'rgbReserved':
                if isinstance(item, uuid.UUID):
                    res[key] = str(item)
                elif isinstance(item, FileChunkReference64x32) or \
                    isinstance(item, FileChunkReference32) or \
                    isinstance(item, FileNodeChunkReference):
                    res[key] = str(item)
                else:
                    res[key] = item
        return res