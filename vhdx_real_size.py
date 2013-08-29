import struct
#constants
HEADER_OFFSETS = [64,128] #in KB
LOG_LENGTH_OFFSET = 68
HEADER_SECTION_SIZE = 1024 ** 2
BAT_ENTRY_SIZE = 8 #B
REGION_TABLE_OFFSET = 192 # in KB
METADATA_FILE_OFFSET = 64 #in B 


def get_max_internal_size(path, size):
    block_size = get_block_size(path)
    logical_sector_size = get_logical_sector_size(path)
    log_size = get_log_size(path)
    metadata_size = get_metadata_size_and_offset(path)[0]
    header_size = HEADER_SECTION_SIZE
    chunk_ratio = (2 ** 23) * logical_sector_size / block_size
    data_blocks_count = (size + block_size - 1) / block_size
    total_bat_entries = data_blocks_count + (data_blocks_count -1)/ chunk_ratio
    bat_size = (total_bat_entries * BAT_ENTRY_SIZE + 1024 ** 2 -1) / 1024 **2
    # considering the 1 MB alignment 
    max_internal_size = size - (header_size + log_size + metadata_size + \
                        bat_size * (1024 ** 2))
    return max_internal_size

def get_current_header_offset(path):
    sequence_number=[]
    try:
        with open(path,'rb') as f:            
            for offset in HEADER_OFFSETS:
                f.seek(offset + 8)
                sequence_number.append(struct.unpack('<Q', f.read(8))[0])
    except IOError:
            print "Unable to get current header"
    finally:
        if f:
            f.close()
    current_header = sequence_number.index(max(sequence_number))
    return HEADER_OFFSETS[current_header]

def get_log_size(path):
    current_header_offset = get_current_header_offset(path)
    offset = current_header_offset * 1024 + LOG_LENGTH_OFFSET
    try:
        with open(path,'rb') as f:
            f.seek(offset)
            log_size = f.read(4)
    except IOError:
        print "Unable to get log length"
    finally:
        if f:
            f.close()
    log_size_value = struct.unpack('<I', log_size)[0]
    return log_size_value

def get_metadata_size_and_offset(path):
    offset = METADATA_FILE_OFFSET + REGION_TABLE_OFFSET * 1024
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            metadata_offset = f.read(8)
            metadata_size = f.read(4)
    except IOError:
        print "Unable to get metadata length and offset"
    finally:
        if f:
            f.close()
    metadata_offset = struct.unpack('<Q', metadata_offset)[0]
    metadata_size = struct.unpack('<I', metadata_size)[0]
    return metadata_size, metadata_offset

def get_block_size(path):
    metadata_offset = get_metadata_size_and_offset(path)[1]
    offset = metadata_offset + 48 
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            file_parameter_offset = struct.unpack('<I', f.read(4))[0]
            f.seek(file_parameter_offset + metadata_offset)
            block_size = struct.unpack('<I', f.read(4))[0]
    except IOError:
        print "Unable to get block size"
    finally:
        if f:
            f.close()
    return block_size

def get_logical_sector_size(path):
    metadata_offset = get_metadata_size_and_offset(path)[1]
    offset = metadata_offset + 48 + 32 * 3
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            logical_sector_offset = struct.unpack('<I', f.read(4))[0]
            f.seek(logical_sector_offset + metadata_offset)
            logical_sector_size = struct.unpack('<I', f.read(4))[0]
    except IOError:
        print "Unable to get block size"
    finally:
        if f:
            f.close()
    return logical_sector_size


'''print "block size: ", get_block_size("c:\\cirros.vhdx")
print "log size: ", get_log_size("c:\\cirros.vhdx")
print "logical sector size", get_logical_sector_size("c:\\cirros.vhdx")
print "max internal size: ", get_max_internal_size("c:\\cirros.vhdx", 1024 ** 3)'''