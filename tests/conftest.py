import subprocess

import pytest


@pytest.fixture
def own_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """Git тестов — свой, а не тот, что позвал хук.

    Коммит через `git commit -a` (так коммитит `cz bump`) выставляет хукам
    `GIT_INDEX_FILE` на временный индекс, и `git add` в репозитории теста писал
    чужие файлы прямо в него — коммит падал на «invalid object».
    """
    local = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    for name in local:
        monkeypatch.delenv(name, raising=False)
