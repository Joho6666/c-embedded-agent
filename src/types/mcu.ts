export interface PeripheralCount {
  name: string;
  count: number;
}

export interface McuInfo {
  id: string;
  name: string;
  family: string;
  core: string;
  frequency: string;
  flashKb: number;
  ramKb: number;
  voltage: string;
  package: string;
  peripherals: PeripheralCount[];
}

export interface PinConfig {
  name: string;
  side: "left" | "right" | "top" | "bottom";
  index: number;
  functions: string[];
  assigned?: string;
  note?: string;
  highlight?: boolean;
}
