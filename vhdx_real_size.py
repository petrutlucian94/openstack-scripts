import struct
#constants
HEADER_OFFSETS = [64,128] #in KB
LOG_LENGTH_OFFSET = 68
HEADER_SECTION_SIZE = 1024 ** 2
BAT_ENTRY_SIZE = 8 #B
REGION_TABLE_OFFSET = 192 # in KB
METADATA_FILE_OFFSET = 64 #in B 


def get_max_internal_size(path, size):
    try:
        with open(path,'rb') as f:
            header_size = HEADER_SECTION_SIZE
            block_size = get_block_size(path, f)
            logical_sector_size = get_logical_sector_size(path, f)
            log_size = get_log_size(path, f)
            metadata_size = get_metadata_size_and_offset(path, f)[0]

            chunk_ratio = (2 ** 23) * logical_sector_size / block_size
            data_blocks_count = (size + block_size - 1) / block_size
            total_bat_entries = data_blocks_count + (data_blocks_count -1) \
                                / chunk_ratio
            bat_size = (total_bat_entries * BAT_ENTRY_SIZE + 1024 ** 2 -1) \
                        / 1024 ** 2 

            max_internal_size = size - (header_size + log_size + \
                                / metadata_size + bat_size * (1024 ** 2))
            return max_internal_size
    except IOError:
        print "Unable to get data from the VHDX file: ", path

def get_current_header_offset(path, handler):
    sequence_number=[]
    for offset in HEADER_OFFSETS:
        handler.seek(offset + 8)
        sequence_number.append(struct.unpack('<Q', handler.read(8))[0])
    current_header = sequence_number.index(max(sequence_number))
    return HEADER_OFFSETS[current_header]

def get_log_size(path, handler):
    current_header_offset = get_current_header_offset(path, handler)
    offset = current_header_offset * 1024 + LOG_LENGTH_OFFSET
    handler.seek(offset) 
    log_size = struct.unpack('<I', handler.read(4))[0]
    return log_size

def get_metadata_size_and_offset(path, handler):
    offset = METADATA_FILE_OFFSET + REGION_TABLE_OFFSET * 1024
    handler.seek(offset)
    metadata_offset = struct.unpack('<Q', handler.read(8))[0]
    metadata_size = struct.unpack('<I', handler.read(4))[0]
    return metadata_size, metadata_offset

def get_block_size(path, handler):
    metadata_offset = get_metadata_size_and_offset(path, handler)[1]
    offset = metadata_offset + 48 
    handler.seek(offset)
    file_parameter_offset = struct.unpack('<I', handler.read(4))[0]
    
    handler.seek(file_parameter_offset + metadata_offset)
    block_size = struct.unpack('<I', handler.read(4))[0]
    return block_size

def get_logical_sector_size(path, handler):
    metadata_offset = get_metadata_size_and_offset(path, handler)[1]
    offset = metadata_offset + 48 + 32 * 3
    handler.seek(offset)
    logical_sector_offset = struct.unpack('<I', handler.read(4))[0]

    handler.seek(logical_sector_offset + metadata_offset)
    logical_sector_size = struct.unpack('<I', handler.read(4))[0]
    return logical_sector_size

'''print "max internal size: ", get_max_internal_size("c:\\cirros.vhdx", 1024 ** 3)'''