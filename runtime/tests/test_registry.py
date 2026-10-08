from charlie.actions.registry import Registry
from charlie.cognition.planner import Action


class StubAdapter:
    def __init__(self) -> None:
        self.opened = []

    def open_app(self, name: str) -> str:
        self.opened.append(name)
        return f"Opened {name}."

    def list_apps(self) -> list[str]:
        return ["Terminal"]

    def open_file(self, path: str) -> str:
        return f"Opened {path}."

    def open_folder(self, path: str) -> str:
        return f"Opened {path}."

    def run_command(self, command: str) -> tuple[str, str, int]:
        return "ok", "", 0

    def quick_switch(self, app: str, query: str, hotkey: str = "k") -> str:
        self.opened.append(f"{app}:{query}:{hotkey}")
        return f"Opened {query} in {app}."

    def compose_message(self, app: str, query: str, message: str, hotkey: str = "f") -> str:
        self.opened.append(f"send:{app}:{query}:{hotkey}:{message}")
        return f"Sent to {query} in {app}."


def test_registry_dispatches_open_app():
    adapter = StubAdapter()
    registry = Registry(adapter=adapter)
    result = registry.execute(Action(tool="os.app.open", args={"name": "Terminal"}))
    assert result.ok is True
    assert adapter.opened == ["Terminal"]
    assert "Terminal" in result.observation


def test_missing_name_is_not_keyerror():
    result = Registry(adapter=StubAdapter()).execute(Action(tool="os.app.open", args={}))
    assert result.ok is False
    assert "name" in result.observation.lower()
    assert result.observation != "'name'"


def test_jump_dispatches():
    adapter = StubAdapter()
    result = Registry(adapter=adapter).execute(
        Action(tool="os.app.jump", args={"app": "Slack", "query": "Arun"})
    )
    assert result.ok is True
    assert "Arun" in result.observation


def test_unknown_tool_fails():
    registry = Registry(adapter=StubAdapter())
    result = registry.execute(Action(tool="not.a.tool", args={}))
    assert result.ok is False


def test_python_run_executes():
    result = Registry(adapter=StubAdapter()).execute(
        Action(tool="python.run", args={"code": "print(1+1)"})
    )
    assert result.ok is True
    assert "2" in result.observation


def test_jump_passes_hotkey():
    adapter = StubAdapter()
    result = Registry(adapter=adapter).execute(
        Action(tool="os.app.jump", args={"app": "WhatsApp", "query": "Arun", "hotkey": "f"})
    )
    assert result.ok is True
    assert adapter.opened == ["WhatsApp:Arun:f"]
