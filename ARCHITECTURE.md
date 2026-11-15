# Apokolips OS — Technical Architecture

**Status:** Draft for project-owner review  
**Project:** Apokolips OS  
**Target:** x86_64 (AMD64), initially tested in Oracle VirtualBox  
**Kernel direction:** Hybrid kernel  
**Implementation principle:** Original Apokolips OS source code; no existing OS kernel as a foundation

---

## 1. Purpose and scope

This document defines the first technical architecture for Apokolips OS. It translates the project vision in `plan.txt` into concrete subsystem boundaries, boot assumptions, interfaces, and staged implementation constraints.

This is an engineering baseline, not a claim that the operating system or any of its subsystems already exist. Decisions marked **provisional** must be validated through implementation and tests. The project owner approves major changes to the architecture.

### 1.1 What “from scratch” means

Apokolips OS will have its own bootloader, kernel, system interfaces, native filesystem, shell, desktop, and applications. It will not use Linux, Windows, BSD, or another operating-system kernel as its foundation, and source code will not be copied from other OS projects or tutorials.

We may use hardware manuals, public technical standards, compiler and assembler toolchains, linkers, debuggers, emulators, and documented protocols. Using these engineering tools does not make Apokolips OS a derivative operating system. Any proposed third-party runtime, library, driver, or source component must be reviewed for necessity, provenance, licence, security, and project-owner approval before adoption.

### 1.2 Initial non-goals

The first bootable milestone will not attempt to provide:
- UEFI boot, Secure Boot, or support for every PC firmware.
- SMP/multi-core scheduling.
- Networking, Wi-Fi, Bluetooth, audio, USB, or broad physical-hardware support.
- A graphical desktop, package manager, or application ecosystem.
- Production-grade security or compatibility with existing operating systems.
- A complete installer or any operation on the host laptop's real disks.

These may be considered in later phases after the basic system is stable.

---

## 2. Architecture overview

Apokolips OS will use a **hybrid-kernel architecture**. The kernel will retain performance- and hardware-critical mechanisms in privileged kernel space, while the design will allow selected higher-level services to move into user space as the process and IPC systems mature.

A hybrid design is not simply “everything in the kernel.” Each service must have a documented reason for its privilege level.

### 2.1 High-level structure

```text
+------------------------------------------------------+
|                  Native Applications                 |
+------------------------------------------------------+
|       Shell / Desktop / User Applications             |
+------------------------------------------------------+
|        User-space Services (introduced later)         |
|  e.g. service managers and selected system services   |
+-------------------- System Calls ---------------------+
|                    KERNEL SPACE                       |
| +----------------+  +-------------------------------+ |
| | Process &      |  | Virtual Memory &              | |
| | Thread Manager |  | Memory Allocator              | |
| +----------------+  +-------------------------------+ |
| | Scheduler      |  | IPC / Synchronisation         | |
| +----------------+  +-------------------------------+ |
| | VFS & Storage  |  | Security / Handle Validation  | |
| +----------------+  +-------------------------------+ |
| | Driver Core & Hardware Abstraction Layer (HAL)     | |
| +----------------------------------------------------+ |
| | CPU / Interrupt / Timer / Architecture Support     | |
| +----------------------------------------------------+ |
+------------------------------------------------------+
|                x86_64 Hardware / VM                   |
+------------------------------------------------------+
```

This is a logical view. The exact placement of individual services may change after their interfaces and failure modes are understood.

### 2.2 Kernel-space responsibilities

Initially, kernel space is responsible for:
- CPU mode setup, descriptor tables, exceptions, and interrupt dispatch.
- Physical and virtual memory management.
- Kernel allocation and safe resource ownership.
- Threads, scheduling, context switching, and process address spaces.
- System-call validation and controlled access to kernel services.
- Core IPC and synchronisation primitives.
- Hardware abstraction, interrupt-facing driver mechanisms, and early drivers.
- The initial VFS and block-device interfaces.
- Kernel diagnostics and controlled panic handling.

### 2.3 User-space responsibilities

As user mode becomes available, user space is intended for:
- Native applications and command-line programs.
- The shell and user-facing utilities.
- Desktop and window-management components.
- Selected services that can communicate through documented IPC interfaces.

A component will move to user space only when the required isolation, IPC, restart/error handling, and resource-management mechanisms exist. Early boot and early kernel milestones may temporarily implement more functionality in kernel space; such temporary placement must be documented rather than mistaken for the final design.

---

## 3. Initial platform and boot contract

### 3.1 Initial target

| Item | Initial decision |
|---|---|
| CPU architecture | x86_64 / AMD64 |
| Firmware path | Legacy BIOS-compatible boot in VirtualBox |
| Execution target | 64-bit long mode for the kernel |
| Initial test environment | VirtualBox virtual machine and virtual disk image |
| Kernel language | C for initial kernel logic; assembly only where low-level CPU control requires it |
| Boot-stage language | x86 assembly |
| Build output | Reproducible raw disk image and/or documented boot image |
| Physical hardware | Not an initial test target |

The BIOS path is a first development target, not a permanent platform limitation. UEFI may be added later through a separately designed firmware interface.

### 3.2 Boot sequence (planned)

The first boot design is a staged BIOS loader:

1. VirtualBox BIOS loads the boot sector from the virtual boot disk.
2. The small first stage performs only the minimum work needed to locate and load the second stage.
3. The second stage obtains the information needed by the kernel and loads the kernel image.
4. The loader establishes a known CPU environment, including the required descriptor tables and transition to x86_64 long mode.
5. The loader prepares a versioned boot-information structure.
6. Control is transferred to the kernel entry point using a documented register and memory contract.
7. The kernel validates the hand-off before using any supplied pointer or memory range.

The exact disk layout, stage sizes, load addresses, and BIOS disk-read strategy will be specified in the bootloader design before implementation. The first-stage size constraint and BIOS compatibility requirements must be treated as hard engineering constraints, not assumptions.

### 3.3 Boot information contract

The bootloader-to-kernel hand-off must be explicit and versioned. The initial structure is expected to carry, as applicable:
- A magic value and structure version.
- The physical memory map and its entry count.
- Kernel image physical and virtual placement information.
- Framebuffer information only if the loader has safely obtained it.
- Boot disk identity or boot-device metadata when available.
- Command-line or boot options, if implemented.
- Any reserved memory ranges that the kernel must not allocate.

Every field must have a defined width, alignment, ownership rule, and validity condition. The kernel must reject an unsupported version or malformed structure safely. The structure must not depend on compiler-specific implicit layout; use fixed-width integer types and explicit padding/alignment rules.

### 3.4 CPU-mode and early-kernel assumptions

The initial kernel is intended to run in x86_64 long mode. Before entering it, the bootloader must establish and document all required CPU state, including:
- A valid GDT and code/data segment setup.
- Paging structures suitable for long mode.
- Required control-register and EFER configuration.
- A known stack with documented alignment.
- A defined kernel entry ABI and register contract.
- A safe interrupt state during the transition.

The kernel must not assume that firmware state, registers, stack contents, or memory mappings are useful unless the boot contract explicitly guarantees them.

---

## 4. CPU architecture and low-level conventions

### 4.1 Architecture layer

Architecture-specific code will be isolated under a dedicated x86_64 area (for example, `kernel/arch/x86_64/`). Generic kernel code should not directly depend on raw port I/O, control-register operations, or x86-specific interrupt-frame layouts.

The architecture layer will own:
- CPU initialization and feature checks.
- GDT, IDT, and exception entry/exit.
- Interrupt controller and timer integration.
- Context-switch assembly.
- CPU-local state.
- Port I/O and memory-mapped I/O primitives.
- Page-table format and architecture-specific TLB operations.

### 4.2 Calling convention and compiler boundary

The compiler's target ABI must be selected and recorded before kernel code is compiled. The provisional choice for C-to-C interfaces is the **System V AMD64 ABI**, provided the selected x86_64-elf toolchain supports it as expected. Assembly entry points must explicitly follow the selected ABI or document their own register contract.

Kernel code must not accidentally use host operating-system headers, libraries, startup files, or runtime assumptions. A freestanding cross-compilation environment will be used. The compiler's generated code and linker output must be inspected during early bring-up.

### 4.3 Interrupt and exception discipline

Interrupt and exception entry code must:
- Preserve the register state required by the documented interrupt-frame format.
- Distinguish CPU-pushed error codes from exceptions that do not push one.
- Avoid calling unsafe or non-reentrant code from interrupt context.
- Keep interrupt handlers short and defer work where appropriate.
- Record enough diagnostic information to identify faults.
- Avoid enabling interrupts until the kernel has installed valid handlers and safe stacks.

---

## 5. Memory architecture

Memory management will be developed in layers.

### 5.1 Physical memory manager

The physical memory manager will consume the validated boot memory map and manage page frames. It must distinguish usable RAM from reserved, firmware, device, and loader-owned ranges. No page may be allocated merely because it appears below the detected RAM limit.

The initial allocator may use a simple bitmap or another clearly testable structure. The final choice will be made with measured memory overhead and implementation complexity in mind.

### 5.2 Virtual memory manager

The virtual memory manager will own x86_64 page tables and mapping permissions. It must define:
- Kernel virtual address layout.
- User address-space layout.
- Physical-to-virtual mapping policy.
- Page permissions and supervisor/user access.
- Mapping and unmapping rules.
- TLB invalidation requirements.
- Guard regions and unmapped fault behaviour.

The initial design should avoid unnecessary address-space complexity. A higher-half kernel is a possible design, but its exact base address and mapping scheme remain **provisional** until the linker layout and boot transition are designed.

### 5.3 Kernel heap

Kernel heap allocation will be layered on top of physical and virtual memory services. Allocation APIs must define alignment, zeroing behaviour, failure behaviour, and ownership. Interrupt-context allocation restrictions must be documented.

### 5.4 Memory safety rules

- Validate all externally supplied addresses and lengths.
- Check integer overflow when calculating sizes and ranges.
- Never trust bootloader structures without validation.
- Keep user pointers distinct from kernel pointers.
- Do not dereference user memory directly without a controlled copy/validation mechanism.
- Test allocator boundaries, exhaustion, fragmentation, and invalid frees.

---

## 6. Processes, threads, scheduling, and IPC

### 6.1 Execution model

A **thread** is the schedulable execution unit. A **process** owns an address space and process-level resources and may contain one or more threads when that capability is implemented.

The first scheduler may support a single CPU and a small number of kernel threads. Multi-core scheduling is explicitly deferred.

### 6.2 Scheduler

The first scheduler should prioritize correctness and observability over advanced policy. A simple pre-emptive round-robin scheduler is a provisional starting point once timer interrupts and context switching are reliable.

The scheduler interface must define:
- Thread states and legal transitions.
- Context representation.
- Ready and waiting queues.
- Yield, block, wake, and exit behaviour.
- Interrupt/pre-emption rules.
- Per-thread stack ownership and cleanup.

### 6.3 System calls

The system-call interface is a stable boundary between user mode and kernel mode. It must define syscall numbers, argument registers or stack layout, return values, error representation, and versioning policy.

Every call must validate arguments, pointers, object handles, permissions, and resource limits. User programs must never be allowed to invoke internal kernel functions directly.

### 6.4 IPC

IPC will be designed around explicit endpoints and validated messages or another documented primitive. The initial implementation may begin with a small synchronous mechanism; asynchronous queues and shared-memory channels can follow when memory isolation is reliable.

IPC must define ownership, message size limits, blocking behaviour, cancellation, peer-death behaviour, and access control.

---

## 7. Hardware abstraction and drivers

The Hardware Abstraction Layer (HAL) separates generic kernel logic from x86_64 and device-specific mechanisms.

### 7.1 Driver model

Drivers must expose documented interfaces and must not allow arbitrary device access by unrelated subsystems. Device discovery, resource assignment, interrupts, DMA, and device lifetime must be explicit.

Initial VirtualBox devices will be selected only after inspecting the VM's configured chipset and controller options. Do not assume a particular graphics adapter, storage controller, or input device without checking the VM configuration.

### 7.2 Initial driver priorities

The initial bring-up sequence is expected to prioritize:
1. Diagnostic text output suitable for early boot.
2. A timer source.
3. Keyboard input.
4. Virtual storage and a block-device abstraction.
5. Basic framebuffer output, when a reliable firmware/VM path is established.

USB, audio, networking, Wi-Fi, Bluetooth, and broad graphics acceleration are deferred.

### 7.3 Driver failure handling

A driver must report initialization failure clearly. Kernel code must not continue using a device whose initialization failed. Timeouts and malformed device responses must not cause unbounded waits.

---

## 8. Storage and filesystem

### 8.1 Block-device layer

The block-device interface will provide bounded read/write operations in logical blocks. It must report device capacity, logical block size, operation status, and errors. All initial write tests must target disposable VirtualBox virtual-disk images.

### 8.2 Native filesystem

Apokolips OS will define its own filesystem format after the block-device layer is testable. The specification must cover:
- On-disk layout and versioning.
- Superblock and metadata structures.
- Allocation and free-space tracking.
- Directories, files, and names.
- Permissions and ownership.
- Crash consistency and recovery strategy.
- Corruption detection and validation tools.

The format must use explicit byte order, field widths, structure sizes, and checksums where appropriate. Disk structures must not be written as arbitrary in-memory C structs without a serialization specification.

### 8.3 Safety

The filesystem must validate every on-disk offset, length, count, and pointer-like reference before use. A test suite must include malformed images, truncated reads, invalid metadata, full-volume conditions, and interrupted-write scenarios.

---

## 9. Graphics, shell, and applications

The shell and desktop are product layers built on documented system services, not privileged shortcuts into kernel internals.

### 9.1 Shell

The native shell will provide command parsing, process launch, environment handling, and useful system diagnostics. The command syntax and scripting capabilities will be designed separately with the project owner.

### 9.2 Graphics and desktop

The graphics stack is expected to progress from basic framebuffer access to drawing primitives, input events, window management, and a desktop environment. The first graphical milestone must work without requiring a GPU driver or hardware acceleration.

The desktop's visual identity, interaction model, accessibility, and window behaviour are product decisions to be made before full implementation.

### 9.3 Native applications

Applications will use documented user-space APIs. Each application must state its system-service dependencies and handle unavailable services gracefully.

---

## 10. Security and reliability model

Security will be built into interfaces rather than added only at the end. The early development system will not be described as secure or production-ready.

Planned controls include:
- Separate kernel and user privilege levels.
- Per-process virtual address spaces.
- Validated system-call arguments.
- Explicit object handles and access checks.
- Memory permission enforcement.
- Resource limits and safe failure paths.
- Filesystem permissions and ownership.
- Diagnostic logs that avoid exposing unnecessary sensitive data.

The kernel must treat user applications, file contents, device responses, and disk metadata as untrusted input.

A kernel panic is a controlled failure mechanism for unrecoverable kernel faults. It should stop unsafe execution and display useful diagnostics; it must not silently continue after memory corruption or critical invariant failure.

---

## 11. Build, development, and test environment

### 11.1 Host and target separation

The development host is currently Windows 11. The target is a virtual x86_64 machine. Host tools are used to build and test the OS; host libraries and host OS services must not become hidden runtime dependencies of the kernel.

The exact toolchain and versions are not frozen in this document. Before implementation, record and verify:
- Cross-compiler target and version.
- Assembler and version.
- Linker and binary utilities.
- Build system and scripting runtime.
- VirtualBox version and VM configuration.
- Debugger and image-generation tools.

A cross-compiler such as an x86_64-elf toolchain is the intended direction. The final selection must be based on reproducible availability on the user's Windows 11 development setup. Toolchain installation instructions will be documented separately.

### 11.2 Build principles

- Use freestanding compilation for kernel and boot components.
- Disable unintended host runtime and standard-library dependencies.
- Use explicit linker scripts and inspect ELF/map output.
- Make builds reproducible and fail on warnings that indicate real defects.
- Keep generated binaries and temporary build output separate from source.
- Record exact commands and tool versions.
- Never commit generated secrets, tokens, or personal machine data.

### 11.3 Test layers

1. **Static checks:** formatting, source review, compiler diagnostics, linker inspection.
2. **Unit tests:** pure logic such as parsers, allocators, and data-structure operations where host-side test harnesses are suitable.
3. **Boot tests:** boot the generated image in a disposable VirtualBox VM.
4. **Integration tests:** exercise interfaces between kernel subsystems.
5. **Fault tests:** malformed input, resource exhaustion, invalid addresses, and device failures.
6. **Regression tests:** rerun relevant tests after every change.

A successful compile alone does not prove that a subsystem works.

### 11.4 Virtual machine safety

- Use a dedicated VM and disposable virtual disks.
- Take snapshots before risky experiments.
- Keep host physical disks disconnected from the experimental VM.
- Do not test an installer or raw-disk writer on the laptop's real storage.
- Record VM firmware mode, chipset, RAM, CPU count, display adapter, and storage controller settings so results can be reproduced.

---

## 12. Proposed repository layout

The repository should grow with implemented features. Do not create empty directories merely to make the tree look complete.

```text
Apokolips-OS/
├── plan.txt
├── ARCHITECTURE.md
├── README.md
├── bootloader/
│   ├── bios/
│   └── common/
├── kernel/
│   ├── arch/
│   │   └── x86_64/
│   ├── core/
│   ├── include/
│   └── mm/
├── drivers/
├── processes/
├── filesystem/
├── security/
├── shell/
├── desktop/
├── applications/
├── libraries/
├── tools/
├── tests/
└── docs/
    ├── specifications/
    └── decision-records/
```

This is a proposed layout. Names and boundaries may be adjusted before the corresponding subsystem is implemented.

---

## 13. Architecture decision records

Major decisions must be recorded under `docs/decision-records/`. Each record should include:
- Decision title and date.
- Status: proposed, accepted, superseded, or rejected.
- Context and problem.
- Options considered.
- Decision and reasons.
- Consequences, risks, and follow-up work.

Initial decisions captured by this document:

| ID | Decision | Status |
|---|---|---|
| ADR-0001 | Build an original OS without using another OS kernel as its base | Accepted project constraint |
| ADR-0002 | Target x86_64 / AMD64 first | Provisional baseline |
| ADR-0003 | Use a hybrid-kernel direction | Provisional baseline |
| ADR-0004 | Start with a BIOS-compatible VirtualBox boot path | Provisional baseline |
| ADR-0005 | Use a freestanding cross-compilation toolchain | Proposed; toolchain selection pending |
| ADR-0006 | Defer SMP, networking, UEFI, and broad hardware support | Initial scope constraint |

These entries are recorded here for clarity. Individual ADR files should be created when the project owner approves the relevant decisions.

---

## 14. Implementation gates and completion criteria

No subsystem is complete merely because code has been written. Each milestone must have:
1. A reviewed specification and interface.
2. Source code with clear ownership and comments where needed.
3. A reproducible build.
4. A test procedure with expected output.
5. Evidence that the test passed.
6. Known limitations and follow-up work.
7. A reviewed Git commit.

### Current bootloader implementation gate

The original BIOS Stage 1 and Stage 2 now assemble into a bounded raw image, and the hosted QEMU/SeaBIOS smoke test confirms that Stage 2 receives a non-zero E820 map. The next gate is not kernel coding: first specify and validate the reserved boot-manifest sector, its checksum and bounds, and how the loader fails on invalid metadata.

Oracle VirtualBox runtime verification remains outstanding. Kernel image loading, long-mode setup, and the kernel hand-off ABI must remain separate, testable milestones. Do not start the scheduler, filesystem, or desktop before a minimal kernel has been loaded and its hand-off validated.

---

## 15. Current status

- Original BIOS Stage 1 and Stage 2 source code is present in the repository.
- The raw 34-sector image builds successfully; hosted image-layout and source tests pass.
- GitHub Actions run #30 successfully booted a diagnostic image under QEMU/SeaBIOS; Stage 2 reported 7 E820 entries.
- Oracle VirtualBox runtime testing is still pending.
- No kernel has been implemented or loaded.
- E820 map normalization, physical allocation, manifest validation, kernel loading, long-mode transition, and kernel hand-off remain future work.
- NASM 3.01, Python 3.14.4, and QEMU 10.2.1 were used in the passing hosted run. The final local Windows/VirtualBox toolchain configuration is not yet verified.
- Architecture choices marked provisional remain subject to project-owner approval.

**Next engineering step:** specify and implement boot-manifest validation as an isolated bootloader milestone. Do not begin kernel loading until the manifest layout, checksum, bounds, and failure cases have independent tests.
