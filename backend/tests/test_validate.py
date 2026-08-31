from pathlib import Path

from app.tools.validate import validate_led_task


def test_led_validator_pc13(tmp_path: Path):
    src = tmp_path / "Core" / "Src"
    src.mkdir(parents=True)
    (src / "main.c").write_text(
        """
#include "main.h"
void MX_GPIO_Init(void);
int main(void) {
  __HAL_RCC_GPIOC_CLK_ENABLE();
  MX_GPIO_Init();
  HAL_GPIO_Init(GPIOC, 0);
  HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
  HAL_Delay(500);
}
""",
        encoding="utf-8",
    )
    r = validate_led_task(tmp_path, "PC13")
    assert r["checks"]["gpio_clock"]
    assert r["checks"]["pin_match"]
    assert r["checks"]["toggle"]
    assert r["checks"]["delay_500"]
    assert r["score"] >= 80
