from app.tools.gcc_parser import parse_gcc_output


def test_parse_error():
    text = "Core/Src/main.c:42:5: error: 'GPIO_PIN_5' undeclared"
    d = parse_gcc_output(text)
    assert d[0]["file"] == "Core/Src/main.c"
    assert d[0]["line"] == 42
    assert d[0]["severity"] == "error"
    assert d[0]["source"] == "gcc"


def test_parse_fatal_and_note():
    text = "\n".join(
        [
            "Core/Src/main.c:1:1: fatal error: stm32f1xx.h: No such file or directory",
            "Core/Src/gpio.c:10:3: warning: unused variable 'x'",
            "Core/Src/gpio.c:10:3: note: in expansion of macro 'FOO'",
        ]
    )
    d = parse_gcc_output(text)
    sevs = [x["severity"] for x in d]
    assert "error" in sevs
    assert "warning" in sevs
    assert "info" in sevs


def test_parse_linker_undefined():
    text = "Core/Src/main.c:12: undefined reference to `HAL_UART_Init'"
    d = parse_gcc_output(text)
    assert d[0]["source"] == "ld"
    assert "HAL_UART_Init" in d[0]["message"]
    assert d[0]["severity"] == "error"


def test_parse_multiple_definition():
    text = "./Core/Src/gpio.c:4: multiple definition of `MX_GPIO_Init'"
    d = parse_gcc_output(text)
    assert d[0]["source"] == "ld"
    assert "MX_GPIO_Init" in d[0]["message"]
