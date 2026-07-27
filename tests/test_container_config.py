import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dependency_name(requirement: str) -> str:
    return re.split(r"[<>=!~\[]", requirement, maxsplit=1)[0].strip().lower()


def test_runtime_requirements_match_project_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = {dependency_name(item) for item in project["project"]["dependencies"]}
    runtime_dependencies = {
        dependency_name(line)
        for line in (ROOT / "requirements.runtime.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert runtime_dependencies == project_dependencies


def test_dockerfiles_install_dependencies_before_source_code() -> None:
    for name in ("Dockerfile.api", "Dockerfile.dashboard"):
        content = (ROOT / name).read_text(encoding="utf-8")
        requirements_copy = content.index("COPY requirements.runtime.txt")
        requirements_install = content.index("pip install --no-cache-dir -r")
        source_copy = content.index("COPY app ./app")
        package_install = content.index("pip install --no-cache-dir --no-deps .")

        assert requirements_copy < requirements_install < source_copy < package_install
