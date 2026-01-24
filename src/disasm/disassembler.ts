import { opcodeTable } from "../core/opcodes";
import { AddressingMode } from "../core/addressing";
import { Bus } from "../core/bus";

export interface DisasmLine {
  address: number;
  bytes: number[];
  text: string;
}

export function disassemble(bus: Bus, start: number, count: number): DisasmLine[] {
  const lines: DisasmLine[] = [];
  let pc = start;
  for (let i = 0; i < count; i += 1) {
    const opcode = bus.read8(pc);
    const def = opcodeTable[opcode];
    if (!def) {
      lines.push({
        address: pc,
        bytes: [opcode],
        text: `.byte $${opcode.toString(16).padStart(2, "0")}`
      });
      pc += 1;
      continue;
    }
    const bytes = [opcode];
    if (def.bytes > 1) {
      bytes.push(bus.read8(pc + 1));
    }
    if (def.bytes > 2) {
      bytes.push(bus.read8(pc + 2));
    }
    const operand = formatOperand(def.mode, bytes);
    lines.push({
      address: pc,
      bytes,
      text: `${def.mnemonic} ${operand}`.trim()
    });
    pc += def.bytes;
  }
  return lines;
}

function formatOperand(mode: AddressingMode, bytes: number[]): string {
  switch (mode) {
    case AddressingMode.Immediate:
      return `#$${bytes[1].toString(16).padStart(2, "0")}`;
    case AddressingMode.ZeroPage:
      return `$${bytes[1].toString(16).padStart(2, "0")}`;
    case AddressingMode.Absolute:
      return `$${bytes[2].toString(16).padStart(2, "0")}${bytes[1]
        .toString(16)
        .padStart(2, "0")}`;
    default:
      return "";
  }
}
