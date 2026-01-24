import { describe, expect, it } from "vitest";
import { Cpu6502 } from "../../src/core/cpu6502";
import { MemoryMap } from "../../src/core/bus";
import { Ram } from "../../src/core/memory";

const RESET_VECTOR = 0xfffc;

function createCpuWithRam(): { cpu: Cpu6502; ram: Ram; bus: MemoryMap } {
  const bus = new MemoryMap();
  const ram = new Ram(0x0000, 0x10000);
  bus.map(ram);
  const cpu = new Cpu6502(bus);
  return { cpu, ram, bus };
}

it("executes LDA immediate and STA absolute", () => {
  const { cpu, ram } = createCpuWithRam();
  ram.write8(RESET_VECTOR, 0x00);
  ram.write8(RESET_VECTOR + 1, 0x80);
  ram.write8(0x8000, 0xa9); // LDA #$42
  ram.write8(0x8001, 0x42);
  ram.write8(0x8002, 0x8d); // STA $1234
  ram.write8(0x8003, 0x34);
  ram.write8(0x8004, 0x12);
  ram.write8(0x8005, 0x00); // BRK

  cpu.reset();
  cpu.stepInstruction();
  cpu.stepInstruction();

  expect(cpu.a).toBe(0x42);
  expect(ram.read8(0x1234)).toBe(0x42);
});

it("handles JSR/RTS stack flow", () => {
  const { cpu, ram } = createCpuWithRam();
  ram.write8(RESET_VECTOR, 0x00);
  ram.write8(RESET_VECTOR + 1, 0x90);
  ram.write8(0x9000, 0x20); // JSR $9005
  ram.write8(0x9001, 0x05);
  ram.write8(0x9002, 0x90);
  ram.write8(0x9003, 0xea); // NOP
  ram.write8(0x9004, 0x00); // BRK
  ram.write8(0x9005, 0xe8); // INX
  ram.write8(0x9006, 0x60); // RTS

  cpu.reset();
  cpu.stepInstruction();
  cpu.stepInstruction();
  cpu.stepInstruction();

  expect(cpu.x).toBe(1);
  expect(cpu.pc).toBe(0x9003);
});
