from pathlib import Path
from typing import ClassVar, List, Optional

from poetry.factory import Factory
from poetry.poetry import Poetry
from poetry.utils.env import Env, EnvManager


class PoetryAPI:
    """TODO"""

    poetry: ClassVar[Poetry]
    env_manager: ClassVar[EnvManager]

    @classmethod
    def init(cls) -> None:
        cls.poetry = Factory().create_poetry(Path(".").absolute())
        cls.env_manager = EnvManager(cls.poetry)

    @classmethod
    def get_active_project_env_version(cls) -> Optional[str]:
        """Return the version of the active poetry env, if it's a poetry env associated with the current project,
        otherwise return None."""
        env = cls._get_active_env()
        if env.path.absolute() not in cls.get_available_env_paths():
            return None
        return cls._get_version_from_venv(env)

    @classmethod
    def get_active_env_path(cls) -> Path:
        return cls._get_active_env().path

    @classmethod
    def get_available_env_names(cls) -> List[str]:
        return [cls._get_version_from_venv(env) for env in cls.env_manager.list()]

    @classmethod
    def is_env_available(cls, version: str) -> bool:
        return version in cls.get_available_env_names()

    @classmethod
    def activate_env(cls, version: str) -> Path:
        return PoetryAPI.env_manager.activate(version).path

    @classmethod
    def remove_env(cls, version: str) -> Path:
        return PoetryAPI.env_manager.remove(version).path

    @staticmethod
    def _get_version_from_venv(venv: Env) -> str:
        return f"{venv.version_info[0]}.{venv.version_info[1]}"

    @classmethod
    def _get_active_env(cls) -> Env:
        return cls.env_manager.get()

    @classmethod
    def get_available_env_paths(cls) -> List[Path]:
        return [env.path.absolute() for env in cls.env_manager.list()]
