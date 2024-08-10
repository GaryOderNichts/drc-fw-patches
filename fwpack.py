#!/usr/bin/env python3
"""
fwpack - Pack/Unpack DRC/DRH firmware files
Created in 2024 by GaryOderNichts
<https://github.com/GaryOderNichts/drc-fw-patches>

Credits to drxtool for the firmware header logic and extracted files structure.
"""

import sys, os
import binascii
import construct

class FirmwareType:
    FIRMWARE_TYPE_DRC = 0x01010000
    FIRMWARE_TYPE_DRH = 0x00010000

BlobHeader = construct.Struct(
    "imageVersion" / construct.Int32ub,
    "blockSize" / construct.Int32ub,
    "sequencePerSession" / construct.Int32ub,
    "imageSize" / construct.Int32ub,
)
assert(BlobHeader.sizeof() == 0x10)

FirmwareHeader = construct.Struct(
    "type" / construct.Int32ul,
    "superCRCs" / construct.Array(4, construct.Int32ul),
    construct.Padding(0xFE8),
    "headerCRC" / construct.Int32ul,
    "subCRCs" / construct.Array(0x1000, construct.Int32ul),
)
assert(FirmwareHeader.sizeof() == 0x5000)

FirmwareSection = construct.Struct(
    "offset" / construct.Int32ul,
    "size" / construct.Int32ul,
    "name" / construct.PaddedString(4, "ascii"),
    "version" / construct.Int32ul,
)
assert(FirmwareSection.sizeof() == 0x10)

FirmwareFile = construct.Struct(
    "blobHeader" / BlobHeader,
    "firmwareHeader" / FirmwareHeader,
    "firmwareData" / construct.Bytes(construct.this.blobHeader.imageSize - FirmwareHeader.sizeof()),
)

# Thanks to drxtool for the crctable logic
def verify_firmware_header(fw) -> bool:
    # Verify header CRC
    header_crc = binascii.crc32(FirmwareHeader.build(fw.firmwareHeader)[0:0xFFC])
    if header_crc != fw.firmwareHeader.headerCRC:
        return False
    
    # Verify super crcs
    subcrc_data = construct.Array(0x1000, construct.Int32ul).build(fw.firmwareHeader.subCRCs)
    for i in range(4):
        super_crc = binascii.crc32(subcrc_data[i*0x1000:i*0x1000+0x1000])
        if super_crc != fw.firmwareHeader.superCRCs[i]:
            return False

    # Verify sub crcs
    for i in range(len(fw.firmwareData) // 0x1000 + 1):
        offset = i * 0x1000
        length = 0x1000
        if len(fw.firmwareData) - offset < length:
            length = len(fw.firmwareData) - offset

        sub_crc = binascii.crc32(fw.firmwareData[offset:offset + length])
        if sub_crc != fw.firmwareHeader.subCRCs[i]:
            return False

    return True

def build_firmware_header(blob_type, firmware_data) -> dict:
    # Calculate CRC for every 0x1000 bytes of firmware data
    sub_crcs = [0] * 0x1000
    for i in range(len(firmware_data) // 0x1000 + 1):
        offset = i * 0x1000
        length = 0x1000
        if len(firmware_data) - offset < length:
            length = len(firmware_data) - offset

        sub_crcs[i] = binascii.crc32(firmware_data[offset:offset + length])

    # Calculate the super CRCs
    super_crcs = [0] * 4
    subcrc_data = construct.Array(0x1000, construct.Int32ul).build(sub_crcs)
    for i in range(4):
        super_crcs[i] = binascii.crc32(subcrc_data[i*0x1000:i*0x1000+0x1000])

    firmware_header = dict(type=blob_type, superCRCs=super_crcs, headerCRC=0, subCRCs=sub_crcs)

    # Calculate the header CRC
    firmware_header["headerCRC"] = binascii.crc32(FirmwareHeader.build(firmware_header)[0:0xFFC])

    return firmware_header

def unpack_firmware(source_file, dest_dir):
    fw = FirmwareFile.parse_file(source_file)
    if not verify_firmware_header(fw):
        print("Firmware header verification failed")
        sys.exit(1)

    if fw.firmwareHeader.type == FirmwareType.FIRMWARE_TYPE_DRC:
        print(f"DRC firmware version 0x{fw.blobHeader.imageVersion:08x}")
    elif fw.firmwareHeader.type == FirmwareType.FIRMWARE_TYPE_DRH:
        print(f"DRH firmware version 0x{fw.blobHeader.imageVersion:08x}")
    else:
        print(f"Unsupported firmware type 0x{fw.firmwareHeader.type:08x}")
        sys.exit(1)

    if not os.path.isdir(dest_dir):
        os.mkdir(dest_dir)

    # Write blob header and type
    BlobHeader.build_file(fw.blobHeader, os.path.join(dest_dir, "blob_header.bin"))
    construct.Int32ul.build_file(fw.firmwareHeader.type, os.path.join(dest_dir, "blob_type.bin"))

    # Assume first part of the data is the index
    index = FirmwareSection.parse(fw.firmwareData)

    # Parse sections
    sections = construct.Array(index.size // FirmwareSection.sizeof(), FirmwareSection).parse(fw.firmwareData)
    for s in sections:
        print(f"Saving {s.name} version 0x{s.version:08x} offset 0x{s.offset} size 0x{s.size}")

        # write section to file
        with open(os.path.join(dest_dir, s.name + ".bin"), "wb") as f:
            f.write(fw.firmwareData[s.offset:s.offset + s.size])

def pack_firmware(source_dir, dest_file):
    # Read blob header and type
    blob_header = BlobHeader.parse_file(os.path.join(source_dir, "blob_header.bin"))
    blob_type = construct.Int32ul.parse_file(os.path.join(source_dir, "blob_type.bin"))

    # Parse sections from INDX
    indx_data = b""
    firmware_data = b""
    sections = construct.GreedyRange(FirmwareSection).parse_file(os.path.join(source_dir, "INDX.bin"))
    
    if len(sections) < 3:
        print(f"Not enough sections. Have {len(sections)} but need at least 3.")
        sys.exit(1)

    if sections[0].name != "INDX":
        print(f"Expected INDX at section 0. This firmware is not bootable!")
        sys.exit(1)

    if sections[2].name != "LVC_":
        print(f"Expected LVC_ at section 2. This firmware is not bootable!")
        sys.exit(1)

    for s in sections:
        print(f"Storing {s.name}...")

        # read section data
        section_data = b""
        with open(os.path.join(source_dir, s.name + ".bin"), "rb") as f:
            section_data = f.read()

        # update section
        s.size = len(section_data)
        s.offset = len(firmware_data)
        firmware_data += section_data

        indx_data += FirmwareSection.build(s)

    # Update INDX data
    firmware_data = indx_data + firmware_data[len(indx_data):]

    # Update total image size
    blob_header.imageSize = FirmwareHeader.sizeof() + len(firmware_data)

    # Build the final image size
    FirmwareFile.build_file(dict(blobHeader=blob_header, firmwareHeader=build_firmware_header(blob_type, firmware_data), firmwareData=firmware_data), dest_file)

if len(sys.argv) != 4:
    print(f"Usage:\n{sys.argv[0]} <unpack/pack> <source> <destination>")
    sys.exit(0)

if sys.argv[1] == "unpack":
    print(f"Unpacking {sys.argv[2]}...")
    unpack_firmware(sys.argv[2], sys.argv[3])
elif sys.argv[1] == "pack":
    print(f"Packing {sys.argv[3]}...")
    pack_firmware(sys.argv[2], sys.argv[3])
else:
    print(f"Unknown mode \"{sys.argv[1]}\"")
    sys.exit(1)
