export interface IocClockNode {
  id: string;
  label: string;
  hz?: number;
  note?: string;
}

export interface IocClockTree {
  hseHz?: number;
  hsiHz?: number;
  pllMul?: number;
  pllSource?: "HSE" | "HSI" | string;
  sysclkHz?: number;
  ahbHz?: number;
  apb1Hz?: number;
  apb2Hz?: number;
  nodes: IocClockNode[];
}

export interface IocPin {
  pin: string;
  signal: string;
  mode?: string;
  peripheral?: string;
  direction?: string;
  locked?: boolean;
}

export interface IocConflict {
  pin: string;
  signals: string[];
  detail: string;
}

export interface IocPeripheral {
  name: string;
  kind: string;
  enabled: boolean;
  params?: Record<string, string>;
}

export interface IocAnalysis {
  filename: string;
  mcu?: string;
  family?: string;
  package?: string;
  board?: string;
  clock?: IocClockTree;
  pins: IocPin[];
  gpio: IocPin[];
  usart: IocPeripheral[];
  spi: IocPeripheral[];
  i2c: IocPeripheral[];
  adc: IocPeripheral[];
  tim: IocPeripheral[];
  pwm: IocPeripheral[];
  dma: IocPeripheral[];
  nvic: string[];
  freertos: boolean;
  middleware: string[];
  conflicts: IocConflict[];
  rawKeys?: number;
}

export interface IocImportResult {
  available: boolean;
  reason?: string;
  projectId?: string;
  analysis?: IocAnalysis;
}
