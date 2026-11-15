; Apokolips OS — BL-2 Stage 2
; BIOS E820 memory-map discovery in 16-bit real mode.
; This remains a bootloader diagnostic stage, not a kernel.

BITS 16
ORG 0x8000

%define E820_BUFFER       0x5000
%define E820_MAX_ENTRIES  32
%define E820_ENTRY_SIZE   24
%define SMAP_SIGNATURE    0x534D4150

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
    mov ah, 0x0E
    mov bx, 0x0007
    int 0x10
    ret

boot_drive:
    db 0
entry_count:
    dw 0

banner:
    db 13, 10, 'APOKOLIPS OS', 13, 10, 0
map_ok:
    db 'BL-2: E820 MEMORY MAP ENTRIES: ', 0
map_error:
    db 'BL-2 ERROR: E820 MEMORY MAP UNAVAILABLE/INVALID', 13, 10, 0
newline:
    db 13, 10, 0
