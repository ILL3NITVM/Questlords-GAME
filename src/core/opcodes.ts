import { AddressingMode } from "./addressing";

export type OpcodeHandler = "LDA" | "LDX" | "LDY" | "STA" | "INX" | "INY" | "JMP" | "JSR" | "RTS" | "NOP" | "BRK";

export interface OpcodeDefinition {
  opcode: number;
  mnemonic: OpcodeHandler;
  mode: AddressingMode;
  bytes: number;
  cycles: number;
}

export const opcodeTable: Record<number, OpcodeDefinition> = {
  0xa9: { opcode: 0xa9, mnemonic: "LDA", mode: AddressingMode.Immediate, bytes: 2, cycles: 2 },
  0xa5: { opcode: 0xa5, mnemonic: "LDA", mode: AddressingMode.ZeroPage, bytes: 2, cycles: 3 },
  0xad: { opcode: 0xad, mnemonic: "LDA", mode: AddressingMode.Absolute, bytes: 3, cycles: 4 },
  0xa2: { opcode: 0xa2, mnemonic: "LDX", mode: AddressingMode.Immediate, bytes: 2, cycles: 2 },
  0xa0: { opcode: 0xa0, mnemonic: "LDY", mode: AddressingMode.Immediate, bytes: 2, cycles: 2 },
  0x85: { opcode: 0x85, mnemonic: "STA", mode: AddressingMode.ZeroPage, bytes: 2, cycles: 3 },
  0x8d: { opcode: 0x8d, mnemonic: "STA", mode: AddressingMode.Absolute, bytes: 3, cycles: 4 },
  0xe8: { opcode: 0xe8, mnemonic: "INX", mode: AddressingMode.Implied, bytes: 1, cycles: 2 },
  0xc8: { opcode: 0xc8, mnemonic: "INY", mode: AddressingMode.Implied, bytes: 1, cycles: 2 },
  0x4c: { opcode: 0x4c, mnemonic: "JMP", mode: AddressingMode.Absolute, bytes: 3, cycles: 3 },
  0x20: { opcode: 0x20, mnemonic: "JSR", mode: AddressingMode.Absolute, bytes: 3, cycles: 6 },
  0x60: { opcode: 0x60, mnemonic: "RTS", mode: AddressingMode.Implied, bytes: 1, cycles: 6 },
  0xea: { opcode: 0xea, mnemonic: "NOP", mode: AddressingMode.Implied, bytes: 1, cycles: 2 },
  0x00: { opcode: 0x00, mnemonic: "BRK", mode: AddressingMode.Implied, bytes: 1, cycles: 7 }
};
