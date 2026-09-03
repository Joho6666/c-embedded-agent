from pathlib import Path

from app.validation import validate_project
from app.validation.review import review_isrs
from app.tools.validate import validate_led_task


def _write_core(tmp: Path, it_c: str, main_c: str | None = None) -> None:
    src = tmp / "Core" / "Src"
    src.mkdir(parents=True)
    (src / "stm32f1xx_it.c").write_text(it_c, encoding="utf-8")
    (src / "main.c").write_text(
        main_c
        or """
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


def test_isr_hal_delay_and_strcpy_fail(tmp_path: Path) -> None:
    _write_core(
        tmp_path,
        """
#include "main.h"
void EXTI0_IRQHandler(void)
{
  char buf[8];
  HAL_Delay(1);
  strcpy(buf, "x");
  HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);
}
""",
    )
    r = review_isrs(tmp_path)
    assert r["checks"]["isr_no_hal_delay"] is False
    assert r["checks"]["isr_no_unsafe_string"] is False
    v = validate_project(tmp_path, "exti")
    assert v["passed"] is False
    assert any("review.isr_no_hal_delay" in m or m == "isr_no_hal_delay" for m in v["missing"]) or "review.isr_no_hal_delay" in str(
        v["missing"]
    )


def test_led_main_delay_still_ok(tmp_path: Path) -> None:
    _write_core(tmp_path, "void HardFault_Handler(void) { while (1) {} }\n")
    led = validate_led_task(tmp_path, "PC13")
    assert led["checks"]["delay_500"]
    r = review_isrs(tmp_path)
    assert r["checks"]["isr_no_hal_delay"] is True
    assert r["checks"]["isr_no_spinloop"] is True
