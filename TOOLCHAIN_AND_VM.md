# Apokolips OS — Toolchain and VirtualBox Setup

**Document status:** BL-0 setup baseline  
**Host:** Windows 11 (project owner's current development machine)  
**Target:** x86_64 BIOS virtual machine  
**Project phase:** Phase 0 / Bootloader milestone BL-0  
**Scope:** Prepare and verify the minimum tools needed for the first 16-bit BIOS boot-sector milestone.

---

## 1. Purpose

This guide establishes a small, reproducible development environment for Apokolips OS on Windows 11. It deliberately avoids installing a large toolchain before it is needed.

For BL-1 (the first 512-byte boot sector), the required tools are:
1. **NASM** — assemble original x86 boot-sector source into a flat binary.
2. **Python 3** — run project-owned image validation and image-building scripts using the standard library.
3. **Oracle VirtualBox** — execute the boot image in an isolated BIOS virtual machine.

A C cross-compiler, linker, ELF utilities, debugger, and kernel build system are **not required for BL-1**. They will be selected and version-pinned before the first kernel-loading milestone. This prevents unnecessary downloads and reduces setup risk on the current 8 GB RAM laptop.

## 2. Host machine constraints and resource budget

The current development host recorded for this project is:
- Windows 11, 64-bit.
- AMD A9-9425 processor.
- 8 GB installed RAM.
- Oracle VirtualBox already installed.
- Python 3.14.7 previously reported by the project owner; this must be rechecked on the active machine.

Recommended initial VM allocation:
- 1 virtual CPU.
- 1024 MB RAM.
- 64 MB dynamically allocated virtual disk.
- 16 MB video memory (not important for text-mode boot tests).
- No audio and no network adapter for the first bootloader test.

These are conservative test settings, not minimum requirements for the eventual OS. Do not allocate most of the host's RAM to the VM.

## 3. Tool selection

### 3.1 NASM

NASM is selected because it assembles x86 instructions and can emit a flat binary with `-f bin`, which is suitable for a BIOS boot sector. NASM is an assembler tool, not an operating-system base.

- Official project site: https://www.nasm.us/
- Official downloads/documentation: https://www.nasm.us/
- Version baseline: **NASM 3.02 stable**, as listed by the official project at the time this document was prepared.
- Install the Windows x64 build appropriate for the host.
- Prefer the official installer or official binary archive. Do not download executables from unofficial download sites.

After installation, ensure the directory containing `nasm.exe` is in the Windows PATH. Open a new PowerShell window after changing PATH.

Verify:

```powershell
nasm -v
where.exe nasm
```

Expected result: NASM prints its version and `where.exe` prints the path to the installed `nasm.exe`.

If the command is not found, reopen PowerShell first. If it is still missing, add the actual NASM installation directory to the user PATH through Windows Environment Variables, then open a new terminal.

### 3.2 Python

Python is used only for host-side build and validation tools. The initial image builder will use Python's standard library, so **pip and third-party Python packages are not needed** for BL-1.

Verify:

```powershell
py --version
py -c "import sys, struct; print(sys.executable); print(sys.version)"
```

Expected result: Python 3.x is reported and the standard-library imports succeed.

The project owner previously reported Python 3.14.7. Keep that version if it is still installed and working. If the active interpreter differs, record the actual version rather than assuming it.

### 3.3 Oracle VirtualBox

VirtualBox is the isolated execution environment for our experimental boot image.

Verify:

```powershell
VBoxManage --version
where.exe VBoxManage
```

If `VBoxManage` is not found, check the normal VirtualBox installation directory, usually:

```text
C:\Program Files\Oracle\VirtualBox\VBoxManage.exe
```

Run it by its full path if necessary. Record the exact installed version in the BL-0 verification record. Do not upgrade VirtualBox solely for this project unless the current version cannot provide the required BIOS VM settings.

Official documentation: https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/

## 4. Create the dedicated Apokolips OS development VM

The VM should be named **Apokolips-Dev-x64-BIOS** so it is clearly separate from any other virtual machines.

Create it in VirtualBox Manager:

1. Select **New**.
2. Name: `Apokolips-Dev-x64-BIOS`.
3. Type: `Other` (or the closest generic type available).
4. Version: choose the generic **64-bit** option if offered. If the UI does not offer it, do not guess or change host firmware settings; report what the UI shows.
5. Do not attach an ISO. This project is not installing an existing operating system.
6. Memory: **1024 MB**.
7. Processors: **1 CPU**.
8. Create a new virtual hard disk:
   - Format: VDI.
   - Allocation: dynamically allocated.
   - Size: **64 MB**.
   - Name: `Apokolips-Dev-BootTest.vdi`.

Then open the VM's **Settings** while it is powered off.

### 4.1 System → Motherboard

- Boot order: Hard Disk first.
- Disable Floppy, Optical, and Network boot entries for the first test if the UI allows.
- Chipset: **PIIX3**.
- Pointing device: leave the default.
- **Enable EFI: OFF**. The first boot target is Legacy BIOS, not UEFI.
- Keep the VM at 1 CPU.

VirtualBox documents the BIOS boot-device order and motherboard settings in its user manual. The exact labels may vary slightly by installed version.

### 4.2 System → Processor

- Processors: 1.
- Leave execution cap at 100%.
- Do not enable nested virtualization for this milestone.

### 4.3 Display

- Graphics controller: leave the default.
- Video memory: 16 MB is sufficient for the initial text-mode boot test.
- 3D acceleration: OFF.

### 4.4 Storage

- Keep the new 64 MB VDI attached to a virtual SATA or IDE controller.
- Do not attach any host physical disk.
- Do not attach the laptop's Windows system drive.
- Do not use raw host-disk mappings.

The project image builder will produce a raw image. Before booting it, the raw image will be converted into a dedicated VDI file using VirtualBox's image conversion tool. The original raw build image remains the canonical test artifact.

### 4.5 Network and audio

- Network: Disabled / Not attached.
- Audio: Disabled.

Neither is needed for the first boot-sector milestone.

### 4.6 Snapshot

After the VM is configured and before first boot testing, take a snapshot named:

```text
BL-0-clean-bios-vm
```

This snapshot is the clean baseline. Take further snapshots before risky changes.

## 5. Project directory layout on Windows

Use one project working directory, for example:

```text
C:\ApokolipsOS\
├── source\
│   └── Apokolips-OS\
├── build\
│   ├── boot\
│   └── images\
├── vm\
│   └── Apokolips-Dev-BootTest.vdi
└── logs\
    └── BL-0\
```

The repository should remain the source of truth. Build output, generated disk images, VM disks, and logs should not be committed unless a specific small test artifact is intentionally approved.

If the repository is already cloned elsewhere, keep it there; the directory above is an example workspace layout, not a requirement to move or duplicate the repository.

## 6. BL-1 build and validation contract

The first source file will be assembled as a raw 16-bit boot-sector binary. The intended command form is:

```powershell
nasm -f bin boot.asm -o boot.bin
```

The build must then validate:
- File size is exactly 512 bytes.
- Byte 510 is `0x55`.
- Byte 511 is `0xAA`.
- No assembler error occurred.
- The binary is written only under the project's build directory.

A simple standard-library validation command can be used:

```powershell
py -c "from pathlib import Path; p=Path('boot.bin'); b=p.read_bytes(); assert len(b)==512, f'expected 512 bytes, got {len(b)}'; assert b[510:512]==bytes((0x55,0xAA)), 'invalid BIOS signature'; print('PASS: 512-byte boot sector and 0x55AA signature')"
```

This validation does not prove that the code boots. A VirtualBox boot test is a separate required check.

## 7. Raw image to VirtualBox VDI

When the project image builder creates a raw image, convert it to a VDI for VM testing. Use the dedicated VM disk path, not a host disk path.

Command form (adjust only the paths to the verified project workspace):

```powershell
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" convertfromraw "C:\ApokolipsOS\build\images\apokolips-boot.img" "C:\ApokolipsOS\vm\Apokolips-Dev-BootTest.vdi" --format VDI
```

Before running the command:
1. Confirm the input is the project's generated raw image.
2. Confirm the output is the VM's dedicated VDI path.
3. Confirm the VM is powered off.
4. Do not overwrite a VDI containing anything valuable.
5. Keep a copy of the raw image for debugging and repeatability.

If the VDI already exists and is attached, do not overwrite it while VirtualBox is using it. Use a new output filename or detach/power off the VM safely first.

## 8. BL-0 verification record

Do not mark BL-0 complete until the project owner has run the checks on the actual laptop. Fill in the actual values; do not guess them.

| Check | Expected | Actual result |
|---|---|---|
| Windows edition/build | Windows 11, 64-bit | Pending |
| NASM | 3.02 stable or approved later stable | Pending |
| Python | Python 3.x, standard library works | Pending |
| VirtualBox | Installed; exact version recorded | Pending |
| VM name | Apokolips-Dev-x64-BIOS | Pending |
| VM firmware | BIOS; EFI disabled | Pending |
| VM RAM | 1024 MB | Pending |
| VM CPUs | 1 | Pending |
| VM disk | Dedicated 64 MB VDI | Pending |
| Host physical disks attached | None | Pending |
| Snapshot | BL-0-clean-bios-vm | Pending |

A tool being listed in this document does not mean it has been installed or verified on the laptop. BL-0 must be confirmed from actual command output and VM settings.

## 9. Troubleshooting

### `nasm` is not recognized

- Confirm NASM installation completed.
- Run `where.exe nasm`.
- Add the real directory containing `nasm.exe` to the user PATH.
- Open a new PowerShell window.
- Run `nasm -v` again.

### `py` is not recognized

- Check whether Python is installed.
- Try `python --version`.
- Use the actual working Python launcher/command consistently and record it.
- Do not install pip packages for BL-1.

### `VBoxManage` is not recognized

- Check `C:\Program Files\Oracle\VirtualBox\VBoxManage.exe`.
- Run the executable using its full path.
- Record the installed VirtualBox version.

### VirtualBox does not offer a 64-bit generic VM type

- Do not change the host BIOS/UEFI settings based on guesswork.
- Record the VirtualBox version and exact options shown.
- Verify hardware virtualization support and VirtualBox configuration before proceeding.

### VM reports no bootable medium

That is expected until a valid boot image has been built, converted, and attached. Do not treat an empty VM as a bootloader failure.

## 10. Safety and originality rules

- All boot tests run in the dedicated virtual machine.
- The VM must contain only the disposable Apokolips virtual disk.
- Never attach the host Windows disk to the VM.
- Never run disk-writing commands against a physical host drive.
- Keep source code original and written for Apokolips OS.
- Do not copy an existing bootloader or tutorial source into the repository.
- Technical manuals and standards may be consulted; document the source of any externally derived technical requirement.
- Do not claim a tool, test, or milestone succeeded until its actual output has been checked.

## 11. BL-0 exit criteria

BL-0 is complete only when:
1. NASM is installed and its version command works.
2. Python runs and standard-library imports succeed.
3. VirtualBox version is recorded and VBoxManage works.
4. The dedicated VM has the documented BIOS settings.
5. The VM uses only a dedicated disposable VDI.
6. The clean baseline snapshot exists.
7. Actual results are recorded in this document or a separate verification log.

**Next milestone:** BL-1 — write the original Apokolips OS Stage 1 assembly source and build a 512-byte boot sector. Do not start Stage 2 or kernel code until BL-1 static checks pass.
