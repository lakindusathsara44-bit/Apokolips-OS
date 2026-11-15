# Apokolips OS — BL-3 BIOS Runtime Smoke Test

**Status:** Implemented in the development branch; CI runtime result pending  
**Target:** x86 BIOS boot path under QEMU with SeaBIOS  
**Prerequisites:** BL-1 image layout and BL-2 E820 diagnostic

## 1. Purpose

BL-3 adds a repeatable hosted BIOS-runtime smoke test. The test boots a disposable raw image under QEMU, waits for Stage 2 to query BIOS INT 15h E820, and verifies that Stage 2 reports at least one valid E820 entry.

This is a test milestone, not a new kernel or a replacement for the VirtualBox test environment.

## 2. Diagnostic-only output

The normal Stage 2 build uses BIOS INT 10h text output only. The CI smoke-test build defines \`QEMU_DEBUGCON\`, which additionally mirrors diagnostic characters to QEMU's debug-console I/O port 0xE9.

The port writes are compiled out of the production Stage 2 image. The debug image is built separately and is used only by the automated test.

## 3. Test flow

1. Assemble the regular Stage 1 and Stage 2 binaries.
2. Build the normal 34-sector disk image.
3. Run all Python static and image-layout tests.
4. Assemble a second Stage 2 with the diagnostic-only QEMU output enabled.
5. Build a separate smoke-test image using the same Stage 1 and image builder.
6. Boot the smoke-test image with QEMU's PC/BIOS machine.
7. Capture debug-console output and require the BL-2 E820 success line with a non-zero hexadecimal entry count.
8. Fail if Stage 2 reports an E820 error, the output is missing, or the count is zero.

The test runner always terminates the QEMU process after its bounded observation window. It does not attach host disks or write to a physical disk.

## 4. What a passing test proves

A passing run demonstrates that, in the selected QEMU/SeaBIOS environment:

- BIOS boot reaches the original Stage 1.
- Stage 1 reads the Stage 2 sectors from the raw image using the configured BIOS disk path.
- Stage 2 executes and can issue the E820 BIOS request.
- Stage 2 receives and reports a non-zero number of E820 records.

## 5. What it does not prove

- It does not prove that every BIOS or physical computer behaves identically.
- It does not replace the planned Oracle VirtualBox BIOS test.
- It does not test UEFI, kernel loading, long-mode transition, or a running kernel.
- It does not prove the returned E820 map is sorted, normalized, or safe for memory allocation.
- It does not establish production readiness.

## 6. Acceptance criteria

1. The normal image builds without QEMU diagnostic port writes.
2. The QEMU diagnostic image assembles and fits in the reserved Stage 2 region.
3. Existing BL-1 image and BL-2 source tests pass.
4. The BIOS smoke test observes the Stage 2 E820 success line.
5. The reported E820 entry count is at least one.
6. The emulator is shut down by the test runner after the observation window.
7. The normal and diagnostic image artifacts are uploaded by CI.
