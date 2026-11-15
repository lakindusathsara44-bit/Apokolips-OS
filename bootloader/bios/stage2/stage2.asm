; Apokolips OS — BL-1 Stage 2
; Original 16-bit real-mode diagnostic payload. This is not a kernel.

BITS 16
ORG 0x8000

stage2_entry:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    cld
    sti

    mov si, banner
    call print_string
    mov si, detail
    call print_string

.halt:
    cli
    hlt
    jmp .halt

print_string:
    mov ah, 0x0E
    mov bx, 0x0007
.next:
    lodsb
    test al, al
    jz .done
    int 0x10
    jmp .next
.done:
    ret

banner:
    db 13, 10, 'APOKOLIPS OS', 13, 10, 0
detail:
    db 'BL-1: STAGE 2 LOADED SUCCESSFULLY', 13, 10
    db 'Bootloader milestone only - kernel not loaded.', 13, 10, 0
