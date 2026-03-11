from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_declares_runtime_and_dev_dependencies():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project = pyproject["project"]

    assert "PyMemoryEditor>=1.5.0" in project["dependencies"]
    assert project["optional-dependencies"]["gui"] == ["PyQt6>=6.7.0"]
    assert project["optional-dependencies"]["memory"] == ["pymem>=1.13"]
    assert "pytest-asyncio>=0.23.0" in project["optional-dependencies"]["dev"]


def test_requirements_txt_is_a_thin_pyproject_wrapper():
    requirements = [
        line.strip()
        for line in (REPO_ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert requirements == [".[dev,gui,memory]"]
