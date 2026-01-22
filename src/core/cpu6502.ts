import { Bus } from "./bus";
import { AddressingMode, resolveAddressing } from "./addressing";
import { opcodeTable } from "./opcodes";
import { StatusFlag, setFlag, updateZeroAndNegative } from "./flags";

export interface CpuState {
  a: number;
  x: number;
  y: number;
  pc: number;
  sp: number;
  status: number;
  cycles: number;
  halted: boolean;
}

export class Cpu6502 {
  a = 0;
  x = 0;
  y = 0;
  pc = 0;
  sp = 0xfd;
  status = StatusFlag.InterruptDisable | StatusFlag.Unused;
  cycles = 0;
  halted = false;

  constructor(private bus: Bus) {}

  reset(): void {
    this.a = 0;
    this.x = 0;
    this.y = 0;
    this.sp = 0xfd;
    this.status = StatusFlag.InterruptDisable | StatusFlag.Unused;
    this.pc = this.read16(0xfffc);
    this.cycles = 0;
    this.halted = false;
  }

  stepInstruction(): number {
    if (this.halted) {
      return 0;
    }

    const opcode = this.bus.read8(this.pc);
    const def = opcodeTable[opcode];
    if (!def) {
      throw new Error(`Unimplemented opcode $${opcode.toString(16).padStart(2, "0")}`);
    }

    const addressing = resolveAddressing(def.mode, this.bus, this.pc);
    const cycles = this.execute(def.mnemonic, def.mode, addressing);
    this.cycles += cycles;
    return cycles;
  }

  getState(): CpuState {
    return {
      a: this.a,
      x: this.x,
      y: this.y,
      pc: this.pc,
      sp: this.sp,
      status: this.status,
      cycles: this.cycles,
      halted: this.halted
    };
  }

  private execute(
    mnemonic: string,
    mode: AddressingMode,
    addressing: { address?: number; value?: number; bytes: number }
  ): number {
    switch (mnemonic) {
      case "LDA": {
        const value = this.readOperand(mode, addressing);
        this.a = value;
        this.status = updateZeroAndNegative(this.status, this.a);
        this.pc += addressing.bytes;
        return 2;
      }
      case "LDX": {
        const value = this.readOperand(mode, addressing);
        this.x = value;
        this.status = updateZeroAndNegative(this.status, this.x);
        this.pc += addressing.bytes;
        return 2;
      }
      case "LDY": {
        const value = this.readOperand(mode, addressing);
        this.y = value;
        this.status = updateZeroAndNegative(this.status, this.y);
        this.pc += addressing.bytes;
        return 2;
      }
      case "STA": {
        if (addressing.address === undefined) {
          throw new Error("STA requires an address");
        }
        this.bus.write8(addressing.address, this.a);
        this.pc += addressing.bytes;
        return 3;
      }
      case "INX": {
        this.x = (this.x + 1) & 0xff;
        this.status = updateZeroAndNegative(this.status, this.x);
        this.pc += 1;
        return 2;
      }
      case "INY": {
        this.y = (this.y + 1) & 0xff;
        this.status = updateZeroAndNegative(this.status, this.y);
        this.pc += 1;
        return 2;
      }
      case "JMP": {
        if (addressing.address === undefined) {
          throw new Error("JMP requires an address");
        }
        this.pc = addressing.address;
        return 3;
      }
      case "JSR": {
        if (addressing.address === undefined) {
          throw new Error("JSR requires an address");
        }
        const returnAddress = (this.pc + 2) & 0xffff;
        this.push((returnAddress >> 8) & 0xff);
        this.push(returnAddress & 0xff);
        this.pc = addressing.address;
        return 6;
      }
      case "RTS": {
        const lo = this.pop();
        const hi = this.pop();
        this.pc = (((hi << 8) | lo) + 1) & 0xffff;
        return 6;
      }
      case "NOP": {
        this.pc += 1;
        return 2;
      }
      case "BRK": {
        this.status = setFlag(this.status, StatusFlag.Break, true);
        this.halted = true;
        this.pc += 1;
        return 7;
      }
      default:
        throw new Error(`Unhandled mnemonic ${mnemonic}`);
    }
  }

  private readOperand(
    mode: AddressingMode,
    addressing: { address?: number; value?: number; bytes: number }
  ): number {
    switch (mode) {
      case AddressingMode.Immediate:
        return addressing.value ?? 0;
      case AddressingMode.ZeroPage:
      case AddressingMode.Absolute:
        return this.bus.read8(addressing.address ?? 0);
      default:
        throw new Error(`Unsupported addressing mode ${mode}`);
    }
  }

  private push(value: number): void {
    this.bus.write8(0x0100 + this.sp, value);
    this.sp = (this.sp - 1) & 0xff;
  }

  private pop(): number {
    this.sp = (this.sp + 1) & 0xff;
    return this.bus.read8(0x0100 + this.sp);
  }

  private read16(address: number): number {
    const lo = this.bus.read8(address);
    const hi = this.bus.read8((address + 1) & 0xffff);
    return (hi << 8) | lo;
  }
}
