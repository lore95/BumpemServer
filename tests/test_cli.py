import pytest

from bumpem import cli


@pytest.mark.parametrize("host,ok", [("127.0.0.1", True), ("localhost", True), ("::1", True), ("127.0.0.2", True),
                                     ("0.0.0.0", False), ("192.168.10.5", False), ("::", False), ("lab-pc", False)])
def test_is_loopback(host, ok):
    assert cli.is_loopback(host) is ok


def test_serve_refuses_network_host_without_flag():
    with pytest.raises(SystemExit) as e:
        cli.main(["serve", "--host", "0.0.0.0", "--board", "sim"])
    assert "D22" in str(e.value)
