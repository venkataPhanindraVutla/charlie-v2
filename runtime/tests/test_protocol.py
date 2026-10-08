import pytest

from charlie.protocol import encode_server, parse_client


def test_parse_user_turn():
    msg = parse_client('{"type":"user.turn","source":"text","text":"open Terminal"}')
    assert msg.type == "user.turn"
    assert msg.source == "text"
    assert msg.text == "open Terminal"


def test_reject_non_json():
    with pytest.raises(ValueError):
        parse_client("not-json")


def test_encode_status():
    raw = encode_server({"type": "status", "state": "thinking"})
    assert '"thinking"' in raw
    assert '"type": "status"' in raw or '"type":"status"' in raw
