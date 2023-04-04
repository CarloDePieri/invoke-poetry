from pathlib import Path
from typing import ClassVar, List, Optional

from poetry.factory import Factory
from poetry.poetry import Poetry
from poetry.utils.env import Env, EnvManager, SystemEnv


class PoetryAPI:
    """TODO"""

    poetry: ClassVar[Poetry]
    env_manager: ClassVar[EnvManager]

    @classmethod
    def init(cls) -> None:
        cls.poetry = Factory().create_poetry(Path(".").absolute())
        cls.env_manager = EnvManager(cls.poetry)

    @classmethod
    def get_active_env_version(cls) -> Optional[str]:
        """Return the version of the active poetry env. Return None if the active env is a system env."""
        env = cls._get_active_env()
        if cls._is_system_env(env):
            return None
        return cls._get_version_from_venv(env)

    @classmethod
    def _is_system_env(cls, env: Env) -> bool:
        return (
            cls.env_manager.get_system_env().path.absolute().resolve()
            == env.path.absolute().resolve()
        )

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
