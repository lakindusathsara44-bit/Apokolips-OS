; Apokolips OS — BL-2/BL-4 Stage 2
; BIOS E820 memory-map discovery and boot-manifest validation.
; This remains a bootloader stage, not a kernel.

BITS 16
ORG 0x8000

%define E820_BUFFER       0x5000
%define E820_MAX_ENTRIES  32
%define E820_ENTRY_SIZE   24
%define SMAP_SIGNATURE       0x534D4150

%define MANIFEST_BUFFER      0x6000
%define MANIFEST_LBA         33
%define MANIFEST_SECTOR_SIZE 512
%define MANIFEST_HEADER_SIZE 32
%define MANIFEST_CRC_OFFSET  28
%define MANIFEST_CRC_END     32
%define MANIFEST_MAGIC_0     0x4B4F5041
%define MANIFEST_MAGIC_1     0x314E414D
%define MANIFEST_VERSION     1
%define MANIFEST_STAGE2_SECTORS 32
%define MANIFEST_PAYLOAD_LBA 34

stage2_entry:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    cld
    sti

    mov [boot_drive], dl

    mov si, banner
    call print_string

    call read_manifest
    jc manifest_read_error

    call validate_manifest
    jc manifest_invalid_error

    mov si, manifest_ok
    call print_string

    call detect_memory_map
    jc memory_map_error

    mov si, map_ok
    call print_string
    mov al, [entry_count]
    call print_hex_byte
    mov si, newline
    call print_string

stage2_halt:
    cli
    hlt
    jmp stage2_halt

; Read reserved manifest sector LBA 33 into physical address 0x6000.
; Return CF=0 on success, CF=1 on BIOS read failure.
read_manifest:
    push ds
    push es
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov si, manifest_dap
    mov dl, [boot_drive]
    mov ah, 0x42
    int 0x13
    pop es
    pop ds
    ret

; Validate the version-1 manifest structure, reserved fields, ranges,
; and CRC32 over the complete 512-byte sector with its CRC field zeroed.
; Return CF=0 only when every check succeeds.
validate_manifest:
    cmp dword [MANIFEST_BUFFER], MANIFEST_MAGIC_0
    jne .invalid
    cmp dword [MANIFEST_BUFFER + 4], MANIFEST_MAGIC_1
    jne .invalid
    cmp word [MANIFEST_BUFFER + 8], MANIFEST_VERSION
    jne .invalid
    cmp word [MANIFEST_BUFFER + 10], MANIFEST_HEADER_SIZE
    jne .invalid
    cmp word [MANIFEST_BUFFER + 12], MANIFEST_STAGE2_SECTORS
    jne .invalid
    cmp word [MANIFEST_BUFFER + 14], 0
    jne .invalid

    ; The future payload must start after the manifest sector.
    ; Reject a 32-bit LBA range overflow. Actual payload loading is BL-6.
    mov eax, [MANIFEST_BUFFER + 16]
    cmp eax, MANIFEST_PAYLOAD_LBA
    jb .invalid
    mov edx, [MANIFEST_BUFFER + 20]
    test edx, edx
    jz .empty_payload
    add eax, edx
    jc .invalid
    jmp .range_valid

.empty_payload:
    ; No payload is present in the current boot image.
    cmp dword [MANIFEST_BUFFER + 24], 0
    jne .invalid

.range_valid:
    ; Version 1 requires all bytes after the fixed header to be zero.
    mov si, MANIFEST_BUFFER + MANIFEST_HEADER_SIZE
    mov cx, MANIFEST_SECTOR_SIZE - MANIFEST_HEADER_SIZE
.reserved:
    cmp byte [si], 0
    jne .invalid
    inc si
    loop .reserved

    call calculate_manifest_crc32
    cmp eax, [MANIFEST_BUFFER + MANIFEST_CRC_OFFSET]
    jne .invalid

    clc
    ret

.invalid:
    stc
    ret

; Standard reflected CRC-32 (polynomial 0xEDB88320).
; The four stored CRC bytes are treated as zero during calculation.
; Returns the calculated CRC in EAX.
calculate_manifest_crc32:
    xor si, si
    mov cx, MANIFEST_SECTOR_SIZE
    mov eax, 0xFFFFFFFF

.byte:
    xor edx, edx
    cmp si, MANIFEST_CRC_OFFSET
    jb .load_byte
    cmp si, MANIFEST_CRC_END
    jb .byte_ready
.load_byte:
    mov dl, [MANIFEST_BUFFER + si]
.byte_ready:
    xor al, dl
    mov bl, 8
.bit:
    shr eax, 1
    jnc .no_polynomial
    xor eax, 0xEDB88320
.no_polynomial:
    dec bl
    jnz .bit
    inc si
    loop .byte

    not eax
    ret

manifest_read_error:
    mov si, manifest_read_error_text
    call print_string
    jmp stage2_halt

manifest_invalid_error:
    mov si, manifest_invalid_error_text
    call print_string
    jmp stage2_halt

; Returns CF=0 on success. E820 records are stored at physical 0x5000.
; The buffer is bounded to 32 entries x 24 bytes (768 bytes).
detect_memory_map:
    mov word [entry_count], 0
    xor ebx, ebx
    mov di, E820_BUFFER

.next_entry:
    cmp word [entry_count], E820_MAX_ENTRIES
    jae .too_many

    ; Request the 24-byte ACPI 3.x form. Set attributes to enabled
    ; before each call for BIOS implementations that preserve them.
    mov dword [es:di + 20], 1
    mov eax, 0xE820
    mov edx, SMAP_SIGNATURE
    mov ecx, E820_ENTRY_SIZE
    ; Preserve segment registers and the destination pointer across BIOS.
    ; EBX is intentionally not restored: BIOS returns the continuation token.
    push ds
    push es
    push di
    int 0x15
    pop di
    pop es
    pop ds
    jc .failed

    cmp eax, SMAP_SIGNATURE
    jne .failed
    cmp ecx, 20
    jb .failed

    inc word [entry_count]
    add di, E820_ENTRY_SIZE

    test ebx, ebx
    jnz .next_entry

    cmp word [entry_count], 0
    je .failed
    clc
    ret

.too_many:
    ; A non-zero continuation token means the map was truncated.
    stc
    ret
.failed:
    stc
    ret

memory_map_error:
    mov si, map_error
    call print_string
    jmp stage2_halt

print_string:
.next:
    lodsb
    test al, al
    jz .done
%ifdef QEMU_DEBUGCON
    out 0xE9, al
%endif
    mov ah, 0x0E
    mov bx, 0x0007
    push si
    int 0x10
    pop si
    jmp .next
.done:
    ret

; Print AL as two uppercase hexadecimal digits.
print_hex_byte:
    push ax
    mov ah, al
    shr al, 4
    call print_hex_nibble
    pop ax
    and al, 0x0F
    call print_hex_nibble
    ret

print_hex_nibble:
    and al, 0x0F
    cmp al, 9
    jbe .digit
    add al, 'A' - 10
    jmp .emit
.digit:
    add al, '0'
.emit:
%ifdef QEMU_DEBUGCON
    out 0xE9, al
%endif
    mov ah, 0x0E
    mov bx, 0x0007
    int 0x10
    ret

boot_drive:
    db 0
entry_count:
    dw 0

align 4
manifest_dap:
    db 0x10, 0
    dw 1
    dw MANIFEST_BUFFER
    dw 0
    dq MANIFEST_LBA

banner:
    db 13, 10, 'APOKOLIPS OS', 13, 10, 0
manifest_ok:
    db 'BL-4: MANIFEST VALID', 13, 10, 0
manifest_read_error_text:
    db 'BL-4 ERROR: MANIFEST READ FAILED', 13, 10, 0
manifest_invalid_error_text:
    db 'BL-4 ERROR: MANIFEST INVALID', 13, 10, 0
map_ok:
    db 'BL-2: E820 MEMORY MAP ENTRIES: ', 0
map_error:
    db 'BL-2 ERROR: E820 MEMORY MAP UNAVAILABLE/INVALID', 13, 10, 0
newline:
    db 13, 10, 0
