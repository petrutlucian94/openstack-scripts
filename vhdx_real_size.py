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
            block_size = get_block_size(f)
            logical_sector_size = get_logical_sector_size(f)
            log_size = get_log_size(f)
            metadata_size = get_metadata_size_and_offset(f)[0]

            chunk_ratio = (2 ** 23) * logical_sector_size / block_size
            data_blocks_count = (size + block_size - 1) / block_size
            total_bat_entries = data_blocks_count + (data_blocks_count -1) \
                                / chunk_ratio
            bat_size = (total_bat_entries * BAT_ENTRY_SIZE + 1024 ** 2 -1) \
                        / 1024 ** 2 

            max_internal_size = size - (header_size + log_size + \
                                 metadata_size + bat_size * (1024 ** 2))
            return max_internal_size
    except IOError:
        print "Unable to get data from the VHDX file: ", path

def get_current_header_offset(file_handler):
    sequence_number=[]
    for offset in HEADER_OFFSETS:
        file_handler.seek(offset + 8)
        sequence_number.append(struct.unpack('<Q', file_handler.read(8))[0])
    current_header = sequence_number.index(max(sequence_number))
    return HEADER_OFFSETS[current_header]

def get_log_size(file_handler):
    current_header_offset = get_current_header_offset(file_handler)
    offset = current_header_offset * 1024 + LOG_LENGTH_OFFSET
    file_handler.seek(offset) 
    log_size = struct.unpack('<I', file_handler.read(4))[0]
    return log_size

def get_metadata_size_and_offset(file_handler):
    offset = METADATA_FILE_OFFSET + REGION_TABLE_OFFSET * 1024
    file_handler.seek(offset)
    metadata_offset = struct.unpack('<Q', file_handler.read(8))[0]
    metadata_size = struct.unpack('<I', file_handler.read(4))[0]
    return metadata_size, metadata_offset

def get_block_size(file_handler):
    metadata_offset = get_metadata_size_and_offset(file_handler)[1]
    offset = metadata_offset + 48 
    file_handler.seek(offset)
    file_parameter_offset = struct.unpack('<I', file_handler.read(4))[0]
    
    file_handler.seek(file_parameter_offset + metadata_offset)
    block_size = struct.unpack('<I', file_handler.read(4))[0]
    return block_size

def get_logical_sector_size(file_handler):
    metadata_offset = get_metadata_size_and_offset(file_handler)[1]
    offset = metadata_offset + 144
    file_handler.seek(offset)
    logical_sector_offset = struct.unpack('<I', file_handler.read(4))[0]

    file_handler.seek(logical_sector_offset + metadata_offset)
    logical_sector_size = struct.unpack('<I', file_handler.read(4))[0]
    return logical_sector_size

print "max internal size: ", get_max_internal_size("c:\\cirros.vhdx", 1024 ** 3)
