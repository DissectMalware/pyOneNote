import uuid
import struct
import Header
import FileNode
jcidEmbeddedFileContainer = b'\x36\x00\x08\x00'
jcidEmbeddedFileContainer_index = 3
jcidPictureContainer14 = b'\x39\x00\x08\x00'
FileNodeListHeaderMagic = b'\xC4\xF4\xF7\xF5\xB1\x7A\x56\xA4'




DEBUG = True

def convert_guid_hex(guid_string):
    return uuid.UUID(guid_string).bytes_le.hex()


def find_index(file_stream, byte_sequence):
    state = 0
    while True:
        if state == len(byte_sequence):
            file_stream.seek(file_stream.tell() - len(byte_sequence))
            return True
        byte = file_stream.read(1)
        if byte != b'':
            if ord(byte) == byte_sequence[state]:
                state += 1
            elif state>0:
                file_stream.seek(file_stream.tell() - state)
                state = 0

        else:
            return False


def parse_string_in_storage_buffer(file):
    res = {}
    res['cch'], = struct.unpack('<I', file.read(4))
    res['StringData'] = file.read(res['cch'] * 2).decode('utf-16')
    return res


def parse_ObjectDeclarationFileData3RefCountFND(file):
    res = {}
    # move to the start of the structure
    file.seek(file.tell() - (jcidEmbeddedFileContainer_index+1))
    res['oid'] = file.read(4)
    res['jcid'] = file.read(4)
    res['cRef'] = ord(file.read(1))

    if(res['cRef'] <= 255):
        # ObjectDeclarationFileData3RefCountFND
        res['FileDataReference'] = parse_string_in_storage_buffer(file)
        if res['FileDataReference']['StringData'].startswith("<ifndf>"):
            res['GUID'] = convert_guid_hex( res['FileDataReference']['StringData'][7:])
        res['Extension'] = parse_string_in_storage_buffer(file)
    else:
        # ObjectDeclarationFileData3LargeRefCountFND
        pass
    return res


file_path = r"C:\Users\aniak\Downloads\835239c095e966bf6037f5755b0c4ed333a163f5cc19ba0bc50ea3c96e0f1628~\SCAN_02_02_#5.one.bin"
# file_path = r"C:\Users\aniak\Downloads\test.bin"
with open(file_path, 'rb') as file:
    header = Header.Header(file)
    root_file_node_list = FileNode.FileNodeList(file, header.fcrFileNodeListRoot)

    file.seek(0)
    while find_index(file, FileNodeListHeaderMagic):
        uintMagic, FileNodeListID, nFragmentSequence = struct.unpack('<8sII', file.read(16))
        root = FileNode.FileNode(file)
        if DEBUG:
            print("FileNodeListHeader " + str(FileNodeListID) + ' ' + str(nFragmentSequence) + ' ' + root.file_node_header.file_node_type)


    while find_index(file, jcidEmbeddedFileContainer):
        print(parse_ObjectDeclarationFileData3RefCountFND(file))

    file.seek(0)
    while find_index(file, jcidPictureContainer14):
        print(parse_ObjectDeclarationFileData3RefCountFND(file))



