export interface PinAssignment {
  pin: string;
  function: string;
  peripheral?: string;
  direction?: "in" | "out" | "analog" | "af";
  mode?: string;
  source: "board" | "user" | "agent";
  note?: string;
}

export interface PinConflict {
  pin: string;
  current: PinAssignment;
  requested: PinAssignment;
}

export interface HardwareContext {
  vendor: string;
  platform: string;
  mcu: string;
  board: string;
  core: string;
  package: string;
  flashKb: number;
  ramKb: number;
  clock: string;
  voltage: string;
  framework: string;
  rtos: string;
  sdkVersion: string;
  buildTool: string;
  projectGenerator: string;
  debugger: string;
  serialPort: string;
  serialBaud: number;
  pins: PinAssignment[];
  peripherals: { name: string; count: number }[];
}
