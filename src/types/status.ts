export type CapabilityStatus =
  | "pass"
  | "fail"
  | "partial"
  | "unknown"
  | "unavailable"
  | "not_tested";

export type InstallStatus = "available" | "not_installed" | "not_configured" | "unknown";

export type SupportStatus = "supported" | "experimental" | "planned";

export type DevicePresence = "connected" | "not_detected" | "available" | "unknown";
