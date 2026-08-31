from app.tools.gcc_parser import parse_gcc_output
from app.workspace.paths import PathEscapeError, resolve_in_root
from pathlib import Path


def test_parse_error():
    text = "Core/Src/main.c:42:5: error: 'GPIO_PIN_5' undeclared"
    d = parse_gcc_output(text)
    assert d[0]["file"] == "Core/Src/main.c"
    assert d[0]["line"] == 42
    assert d[0]["severity"] == "error"


def test_path_escape(tmp_path: Path):
    try:
        resolve_in_root(tmp_path, "../etc/passwd")
        assert False
    except PathEscapeError:
        pass
