# drc-fw-patches
Patches for the Wii U gamepad firmware.

## Disclaimer
Modifying the DRC firmware can cause permanent damage.  
No one but yourself is responsible for any sort of damage resulting from using these patches.

## Usage
### Requirements
- make
- [armips](https://github.com/Kingcom/armips)
- python3
- python-construct

Place the original `drc_fw.bin` version `0x190c0117` from your MLC or NUS into this directory.  
Running `make` will build a `patched_drc_fw.bin` which can be flashed to the gamepad.
