# Questlords 6502 IDE Architecture

## Overview
This repository is structured to keep the 6502 core, assembler, and tooling framework-agnostic. The UI imports the core modules but does not couple to them, enabling Node-based tests and future integration into other runtimes.

## Milestone 1 Scope
- Core CPU registers, reset flow, and a minimal opcode subset.
- Memory bus abstraction with RAM/ROM regions.
- Minimal disassembler for UI scaffolding.

Future milestones expand into full opcode coverage, cycle accuracy, assembler, debugger UI, and simulator introspection.
