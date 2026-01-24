import { MemoryRegion } from "./memory";

export interface Bus {
  read8(address: number): number;
  write8(address: number, value: number): void;
  peek8?(address: number): number;
}

export class MemoryMap implements Bus {
  private regions: MemoryRegion[] = [];

  map(region: MemoryRegion): void {
    this.regions.push(region);
  }

  read8(address: number): number {
    const region = this.resolve(address);
    return region.read8(address - region.start);
  }

  write8(address: number, value: number): void {
    const region = this.resolve(address);
    region.write8(address - region.start, value);
  }

  peek8(address: number): number {
    const region = this.resolve(address);
    return region.peek8(address - region.start);
  }

  private resolve(address: number): MemoryRegion {
    const region = this.regions.find(
      (entry) => address >= entry.start && address <= entry.end
    );
    if (!region) {
      throw new Error(`Unmapped address $${address.toString(16).padStart(4, "0")}`);
    }
    return region;
  }
}
