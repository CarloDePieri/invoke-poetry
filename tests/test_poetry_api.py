import pytest
from _pytest.config import ExitCode

#
# These are SLOW, since they need to create several virtualenv to check poetry interoperability
#
pytestmark = [pytest.mark.slow]


class TestAPoetryApi:
    """Test: A poetry api..."""

    def test_should_be_able_to_construct_an_object_representing_the_project(
        self, pytester, inv_bin, add_test_file
    ):
        """A poetry api should be able to construct an object representing the project."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke import task
            from invoke_poetry.poetry_api import PoetryAPI
            
            # noinspection PyUnusedLocal
            @task(name="test")
            def test_task(c):
                PoetryAPI.init()
                assert hasattr(PoetryAPI.poetry, "VERSION")
                assert hasattr(PoetryAPI.env_manager, "ENVS_FILE")
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_automatically_setup_by_init_ns(
        self, pytester, inv_bin, add_test_file
    ):
        """A poetry api should be automatically setup by init_ns."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            # noinspection PyUnusedLocal
            @task(name="test")
            def test_task(c):
                assert PoetryAPI.poetry
                assert PoetryAPI.env_manager
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_return_the_active_env_version(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to return the active env version."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task(name="test")
            def test_task(c):
                assert PoetryAPI.get_active_project_env_version() is None
                c.run("{poetry_bin_str} env use 3.9")
                assert PoetryAPI.get_active_project_env_version() == "3.9"
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_return_the_active_env_path(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to return the active env path."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task(name="test")
            def test_task(c):
                c.run("{poetry_bin_str} env use 3.9")
                assert "3.9" == PoetryAPI.get_active_env_path().name[-3:]
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_list_available_poetry_envs(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to list available poetry envs."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task(name="test")
            def test_task(c):
                assert len(PoetryAPI.get_available_env_names()) == 0
                c.run("{poetry_bin_str} env use 3.8")
                c.run("{poetry_bin_str} env use 3.9")
                assert PoetryAPI.get_available_env_names() == ["3.8", "3.9"]
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_list_available_poetry_envs_paths(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to list available poetry envs' paths."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task(name="test")
            def test_task(c):
                assert len(PoetryAPI.get_available_env_names()) == 0
                versions = ["3.8", "3.9"]
                for version in versions:
                    c.run("{poetry_bin_str} env use " + version)
                paths = [str(p) for p in PoetryAPI.get_available_env_paths()]
                assert len(paths) == 2
                for i, path in enumerate(paths):
                    assert "/tmp" == path[:4]
                    assert versions[i] in str(path)
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_tell_if_a_poetry_env_is_available(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to tell if a poetry env is available."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task(name="test")
            def test_task(c):
                version = "3.9"
                assert not PoetryAPI.is_env_available(version)
                c.run("{poetry_bin_str}" + f" env use {{version}}")
                assert PoetryAPI.is_env_available(version)
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_activate_a_venv(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to activate a venv."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            # noinspection PyUnusedLocal
            @task(name="test")
            def test_task(c):
                version = "3.9"
                assert len(PoetryAPI.get_available_env_names()) == 0
                assert PoetryAPI.get_active_project_env_version() is None
                env_path = PoetryAPI.activate_env(version=version)
                assert version in str(env_path)
                assert PoetryAPI.get_available_env_names() == [version]
                assert PoetryAPI.get_active_project_env_version() == version
                assert version in c.run("{poetry_bin_str} env info -p").stdout
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_be_able_to_remove_a_poetry_env(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """A poetry api should be able to remove a poetry env."""

        # language=python prefix="if True:" # IDE language injection
        test_source = f"""
            from invoke_poetry import init_ns
            from invoke_poetry.poetry_api import PoetryAPI
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            # noinspection PyUnusedLocal
            @task(name="test")
            def test_task(c):
                version = "3.9"
                c.run("{poetry_bin_str} env use " + version)
                assert len(PoetryAPI.get_available_env_names()) == 1
                deleted = PoetryAPI.remove_env(version=version)
                assert version in str(deleted)
                assert len(PoetryAPI.get_available_env_names()) == 0
            """
        add_test_file(test_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK
