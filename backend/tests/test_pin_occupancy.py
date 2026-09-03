from pathlib import Path

from app.tools.periph_gen import configure_peripheral, pin_occupancy


def test_pwm_then_exti_conflicts_on_pa0(tmp_path: Path) -> None:
    (tmp_path / "Core" / "Inc").mkdir(parents=True)
    (tmp_path / "Core" / "Src").mkdir(parents=True)
    (tmp_path / "Makefile").write_text(
        "C_SOURCES = \\\n\tCore/Src/gpio.c \\\n\tCore/Src/main.c\n",
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Inc" / "stm32f1xx_hal_conf.h").write_text(
        "#define HAL_GPIO_MODULE_ENABLED\n#define HAL_TIM_MODULE_ENABLED\n",
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Src" / "stm32f1xx_it.c").write_text(
        '#include "main.h"\nvoid SysTick_Handler(void) { HAL_IncTick(); }\n',
        encoding="utf-8",
    )
    (tmp_path / "Core" / "Inc" / "stm32f1xx_it.h").write_text(
        "#ifndef IT_H\n#define IT_H\nvoid SysTick_Handler(void);\n#endif\n",
        encoding="utf-8",
    )
    pwm = configure_peripheral(tmp_path, "pwm", {})
    assert pwm.get("ok") is True
    occ = pin_occupancy(tmp_path)
    assert "PA0" in occ
    exti = configure_peripheral(tmp_path, "exti", {"pin": "PA0"})
    assert exti.get("ok") is False
    assert exti.get("conflicts")
    assert any(c.get("pin") == "PA0" for c in exti["conflicts"])
    forced = configure_peripheral(tmp_path, "exti", {"pin": "PA0", "force": True})
    assert forced.get("ok") is True
