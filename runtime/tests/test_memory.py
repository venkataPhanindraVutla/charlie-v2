from charlie.memory.store import Store


def test_low_score_is_not_stored(tmp_path):
    store = Store(tmp_path / "charlie.db")
    wrote = store.maybe_write_memory("opened chrome", score=0.2)
    assert wrote is False
    assert store.memory_count() == 0


def test_turns_round_trip(tmp_path):
    store = Store(tmp_path / "charlie.db")
    store.add_turn("user", "open slack")
    store.add_turn("assistant", "Slack is open.")
    turns = store.recent_turns()
    assert turns[0]["role"] == "user"
    assert turns[1]["text"] == "Slack is open."


def test_high_score_is_stored(tmp_path):
    store = Store(tmp_path / "charlie.db")
    wrote = store.maybe_write_memory("Songs live in ~/Music/Anime", score=0.9)
    assert wrote is True
    assert store.memory_count() == 1
