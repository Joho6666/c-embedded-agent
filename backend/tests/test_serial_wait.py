from app.tools import serialutil


def test_wait_for_without_port_returns_empty_immediately() -> None:
    serialutil.disconnect()
    t0 = __import__("time").time()
    lines = serialutil.wait_for(expect="CEA:USART:PASS", max_s=8.0)
    assert lines == []
    assert (__import__("time").time() - t0) < 1.0


def test_wait_for_expect_on_buffered_lines() -> None:
    serialutil.disconnect()
    serialutil._session["lines"].clear()
    serialutil._session["lines"].append({"text": "boot"})
    serialutil._session["lines"].append({"text": "CEA:USART:PASS"})
    lines = serialutil.wait_for(expect="CEA:USART:PASS", max_s=8.0)
    assert any("CEA:USART:PASS" in x for x in lines)
