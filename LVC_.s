.arm.little

.open "unpacked/LVC_.bin",0

; Patches configuration
ADD_UIC_CONFIG_REGION equ 1
ADD_UIC_CONFIG_BOARD_CONFIG equ 1

.if ADD_UIC_CONFIG_REGION
.notice "Adding region to UIC config"

; Patch jumptable to make ID 1 valid
.org 0x0003c9c4
    .d8 0x30

; Patch config table at offset 1 to insert region
.org 0x000b28d0
    .d32 0x3   ; size
    .d32 0x103 ; eeprom offset
.endif

.if ADD_UIC_CONFIG_BOARD_CONFIG
.notice "Adding board config to UIC config"

; Patch jumptable to make ID 4 valid
.org 0x0003c9c7
    .d8 0x30

; Patch config table at offset 4 to insert board config
.org 0x000b28e8
    .d32 0x3   ; size
    .d32 0x106 ; eeprom offset
.endif

.close
