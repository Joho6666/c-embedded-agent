import { describe, expect, it } from "vitest";
import { disabledReason } from "./capabilities";
import { getPlatform } from "./catalog";

describe("toolbar capabilities", () => {
  it("disables flash on Host C", () => {
    const why = disabledReason(getPlatform("host-c"), "flash", "live");
    expect(why).toMatch(/暂不支持|尚未实现/);
  });

  it("disables build on ESP32 even when live", () => {
    const why = disabledReason(getPlatform("esp32"), "build", "live");
    expect(why).toBeTruthy();
  });

  it("refuses real build in DEMO", () => {
    const why = disabledReason(getPlatform("stm32"), "build", "demo");
    expect(why).toMatch(/DEMO/);
  });

  it("allows STM32 build when live", () => {
    expect(disabledReason(getPlatform("stm32"), "build", "live")).toBeNull();
  });
});
