export interface Register {
  name: string;
  value: string;
}

export interface WatchVar {
  name: string;
  value: string;
}

export interface CallStackFrame {
  name: string;
  location: string;
}

export interface SerialLine {
  ts: string;
  text: string;
}

export interface CodeFile {
  path: string;
  language: string;
  content: string;
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "folder";
  children?: FileNode[];
}

export interface TestCase {
  name: string;
  status: "pass" | "fail" | "skip";
  durationMs: number;
  message?: string;
}

export interface TestSuite {
  name: string;
  passed: number;
  failed: number;
  skipped: number;
  coverage: number;
  cases: TestCase[];
}
