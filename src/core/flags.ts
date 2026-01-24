export enum StatusFlag {
  Carry = 0x01,
  Zero = 0x02,
  InterruptDisable = 0x04,
  Decimal = 0x08,
  Break = 0x10,
  Unused = 0x20,
  Overflow = 0x40,
  Negative = 0x80
}

export function setFlag(status: number, flag: StatusFlag, enabled: boolean): number {
  return enabled ? status | flag : status & ~flag;
}

export function getFlag(status: number, flag: StatusFlag): boolean {
  return (status & flag) !== 0;
}

export function updateZeroAndNegative(status: number, value: number): number {
  const zero = (value & 0xff) === 0;
  const negative = (value & 0x80) !== 0;
  let updated = setFlag(status, StatusFlag.Zero, zero);
  updated = setFlag(updated, StatusFlag.Negative, negative);
  return updated;
}
