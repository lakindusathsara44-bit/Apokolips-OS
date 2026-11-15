; Apokolips OS — BL-1 Stage 1 BIOS boot sector
; x86 BIOS, 16-bit real mode. Loads LBA 1..32 to physical 0x8000.

BITS 16
ORG 0x7C00

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    cld
    sti
    mov [boot_drive], dl

    ; Check BIOS Enhanced Disk Drive extensions.
    mov ah, 0x41
    mov bx, 0x55AA
    mov dl, [boot_drive]
    int 0x13
    jc edd_error
    cmp bx, 0xAA55
    jne edd_error
    test cx, 1
    jz edd_error

    ; Load the fixed 16 KiB Stage 2 region.
    mov si, disk_address_packet
    mov dl, [boot_drive]
    mov ah, 0x42
    int 0x13
    jc disk_error
    jmp 0x0000:0x8000

edd_error:
    mov si, msg_edd
    jmp print_error
disk_error:
    mov si, msg_disk

print_error:
    mov ah, 0x0E
    mov bx, 0x0007
.next:
    lodsb
    test al, al
    jz .halt
    int 0x10
    jmp .next
.halt:
    cli
    hlt
    jmp .halt

boot_drive:
    db 0
align 4
disk_address_packet:
    db 0x10, 0
    dw 32
    dw 0x8000
    dw 0x0000
    dq 1

msg_edd:  db 'APOKOLIPS: EDD NOT AVAILABLE', 0
msg_disk: db 'APOKOLIPS: STAGE 2 READ FAILED', 0

times 510 - ($ - $$) db 0
dw 0xAA55
