import { Bus } from "./bus";

export enum AddressingMode {
  Implied = "Implied",
  Immediate = "Immediate",
  Absolute = "Absolute",
  ZeroPage = "ZeroPage"
}

export interface AddressingResult {
  address?: number;
  value?: number;
  bytes: number;
}

export function resolveAddressing(
  mode: AddressingMode,
  bus: Bus,
  pc: number
): AddressingResult {
  switch (mode) {
    case AddressingMode.Implied:
      return { bytes: 1 };
    case AddressingMode.Immediate:
      return { value: bus.read8(pc + 1), bytes: 2 };
    case AddressingMode.ZeroPage:
      return { address: bus.read8(pc + 1), bytes: 2 };
    case AddressingMode.Absolute: {
      const lo = bus.read8(pc + 1);
      const hi = bus.read8(pc + 2);
      return { address: (hi << 8) | lo, bytes: 3 };
    }
  }
}
