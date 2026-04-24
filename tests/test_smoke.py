import importlib.util
from pathlib import Path


def _load_main_module():
    module_path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("dex_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_prints_greeting(capsys):
    module = _load_main_module()

    module.main()

    captured = capsys.readouterr()
    assert captured.out == "Hello from dex!\n"
