# Questlords 6502 IDE

A production-quality, browser-based 6502 emulator + simulator + programmable IDE. This repository now contains the scaffolding and Milestone 1 core CPU implementation.

## Getting Started

```bash
npm install
npm run dev
```

## Single-file demo

Open `standalone.html` directly in a browser to run a minimal, build-free demo of the 6502 core.

## Tests

```bash
npm test
```

## Milestone 1 Deliverables
- Core CPU with basic opcode subset and reset behavior.
- Bus abstraction with RAM/ROM memory regions.
- Minimal disassembler for UI integration.
- React + Vite scaffolding for the IDE shell.
