DRC_FW_FILE := drc_fw.bin
LVC_SHA256 := "d83be494af0bb35cc4bd3340a3da3adb0823bcf111d6e2fd72092a0532d8df32  unpacked/LVC_.bin"

.PHONY: unpack patch pack clean

all: pack
	@echo "All done!"

unpack:
	@echo "Unpacking firmware..."
	@python3 fwpack.py unpack $(DRC_FW_FILE) unpacked

	@echo "Checking LVC_.bin..."
	@echo $(LVC_SHA256) | sha256sum -c -

patch: unpack
	@echo "Patching LVC_.bin"
	@armips LVC_.s

	@echo "Patching versions..."
# patch version to 254.0.0 (blob_header.bin is big endian, VER_.bin is little endian)
	@env printf '\xfe\x00\x00\x00' | dd of=unpacked/blob_header.bin bs=1 seek=0 count=4 conv=notrunc
	@env printf '\x00\x00\x00\xfe' | dd of=unpacked/VER_.bin bs=1 seek=0 count=4 conv=notrunc

pack: patch
	@echo "Packing firmware..."
	@python3 fwpack.py pack unpacked patched_$(DRC_FW_FILE)

clean:
	@echo "Clean..."
	@rm -rf unpacked patched_$(DRC_FW_FILE)
