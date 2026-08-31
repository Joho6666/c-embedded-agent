from app.mcu.stm32f103 import get_mcu_info, get_pin_info


def test_mcu_info():
    info = get_mcu_info()
    assert info["name"] == "STM32F103C8T6"
    assert info["flash_kb"] == 64
    assert info["ram_kb"] == 20
    assert "USART1" in info["peripherals"]


def test_pin_usart1():
    pa9 = get_pin_info("PA9")
    assert pa9["found"]
    assert "USART1_TX" in pa9["functions"]
    pa10 = get_pin_info("PA10")
    assert "USART1_RX" in pa10["functions"]
    pc13 = get_pin_info("PC13")
    assert pc13["found"]
