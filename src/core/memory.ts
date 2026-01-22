export interface MemoryRegion {
  readonly start: number;
  readonly end: number;
  read8(offset: number): number;
  write8(offset: number, value: number): void;
  peek8(offset: number): number;
}

export class Ram implements MemoryRegion {
  readonly start: number;
  readonly end: number;
  private data: Uint8Array;

  constructor(start: number, size: number) {
    this.start = start;
    this.end = start + size - 1;
    this.data = new Uint8Array(size);
  }

  read8(offset: number): number {
    return this.data[offset] ?? 0;
  }

  write8(offset: number, value: number): void {
    this.data[offset] = value & 0xff;
  }

  peek8(offset: number): number {
    return this.data[offset] ?? 0;
  }

  load(bytes: Uint8Array, offset = 0): void {
    this.data.set(bytes, offset);
  }
}

export class Rom implements MemoryRegion {
  readonly start: number;
  readonly end: number;
  private data: Uint8Array;

  constructor(start: number, data: Uint8Array) {
    this.start = start;
    this.data = data;
    this.end = start + data.length - 1;
  }

  read8(offset: number): number {
    return this.data[offset] ?? 0;
  }

  write8(): void {
    // ROM ignores writes
  }

  peek8(offset: number): number {
    return this.data[offset] ?? 0;
  }
}
