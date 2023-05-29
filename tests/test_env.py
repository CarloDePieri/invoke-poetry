import shutil
from pathlib import Path
from typing import List

import pytest
from _pytest.config import ExitCode


class TestRememberActiveEnv:
    """Test: remember_active_env..."""

    def test_should_go_back_to_the_previous_poetry_env(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """remember_active_env should go back to the previous poetry env."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, remember_active_env
            
            ns, task = init_ns("3.8")
                    
            @task(name="remember")
            def test_task(c):
                c.run("{poetry_bin_str} env use 3.8")
                with remember_active_env():
                    c.run("{poetry_bin_str} env use 3.9")
                    assert "3.9" in c.run("{poetry_bin_str} run python --version").stdout
                after = c.run("{poetry_bin_str} run python --version").stdout
                assert "3.8" in after
                assert "3.9" not in after
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "remember")
        assert result.ret == ExitCode.OK

    def test_should_not_change_back_the_env_if_no_poetry_env_was_active_before(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """remember_active_env should not change back the env if no poetry env was active before."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, remember_active_env
            
            ns, task = init_ns("3.8")
                    
            @task(name="remember")
            def test_task(c):
                with remember_active_env():
                    c.run("{poetry_bin_str} env use 3.9")
                    assert "3.9" in c.run("{poetry_bin_str} run python --version").stdout
                after = c.run("{poetry_bin_str} run python --version").stdout
                assert "3.8" not in after
                assert "3.9" in after
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "remember")
        assert result.ret == ExitCode.OK


class TestEnvOperation:
    """Test: env operation..."""

    versions: List[str] = ["3.8", "3.9", "3.10"]
    test_root: Path

    @pytest.fixture(autouse=True)
    def setup(self, request, add_test_file, poetry_bin_str):
        """TestEnvOperation single test setup"""
        versions = self.versions
        # language=python prefix="versions=[] if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns
            
            ns, task = init_ns("{versions[0]}", {versions}, poetry_bin="{poetry_bin_str}")
            """
        task_file = add_test_file(source=task_source, debug_mode=False)
        request.cls.test_root = task_file.parent

    def _add_dummy_dependency(self, poetry_bin, pytester):
        """Add a dummy package to the dev dependencies."""
        venvs_folder = self.test_root / ".venvs"
        pytester.run(
            *poetry_bin, "add", "--group", "dev", "dummy-pip-package", "--lock"
        )
        if venvs_folder.is_dir():
            shutil.rmtree(venvs_folder)
            (venvs_folder.parent / "poetry.lock").unlink(missing_ok=True)

    def test_list_should_show_all_poetry_envs(self, pytester, inv_bin, poetry_bin):
        """Env operation list should show all poetry envs."""
        for version in self.versions:
            pytester.run(*poetry_bin, "env", "use", version)
        result = pytester.run(*inv_bin, "env.list")

        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines_random(
            [r".*" + v.replace(".", r"\.") for v in self.versions[:-1]]
            + [
                r".*" + v.replace(".", r"\.") + ".*activated"
                for v in [self.versions[-1]]
            ]
        )

    def test_init_should_be_able_to_init_a_specific_env(
        self, pytester, inv_bin, poetry_bin
    ):
        """Env operation init should be able to init a specific env."""
        venvs_folder = self.test_root / ".venvs"

        # Add a dummy dev dependency
        self._add_dummy_dependency(poetry_bin, pytester)

        # No env folder should be present at this point
        assert not venvs_folder.is_dir()

        # init the 3.8 env
        result = pytester.run(*inv_bin, "env.init")
        assert result.ret == ExitCode.OK
        pytester.run(*inv_bin, "env")  # ???? TODO

        # check that a poetry env for 3.8 has been created
        venv_folder = next(venvs_folder.glob("./test*py" + self.versions[0]))
        assert venv_folder.is_dir()  # the envs folder contains a poetry env for 3.8

        # check that the dependencies has been installed in the correct env
        result = pytester.run(*poetry_bin, "run", "which", "dummy-pip-package")
        bin_file = Path(result.outlines[0])
        assert bin_file.is_file()
        assert bin_file.parent.parent == venv_folder

    def test_init_should_create_and_install_all_needed_envs(
        self, pytester, inv_bin, poetry_bin
    ):
        """Env operation init should create and install all needed envs."""
        # Add a dummy dev dependency
        self._add_dummy_dependency(poetry_bin, pytester)

        venvs_folder = self.test_root / ".venvs"

        # No env folder should be present at this point
        assert not venvs_folder.is_dir()

        pytester.run(*inv_bin, "env.init", "-a")

        for version in self.versions:
            venv_folder = next(venvs_folder.glob("./test*py" + version))
            assert venv_folder.is_dir()  # the envs folder contains a poetry env for 3.8

            # check that the dependencies has been installed in the correct env
            pytester.run(*poetry_bin, "env", "use", version)
            result = pytester.run(*poetry_bin, "run", "which", "dummy-pip-package")
            bin_file = Path(result.outlines[0])
            assert bin_file.is_file()
            assert bin_file.parent.parent == venv_folder

    def test_init_should_switch_to_the_new_env(self, pytester, inv_bin, poetry_bin):
        """Env operation init should switch to the new env."""
        version = self.versions[1]
        pytester.run(*inv_bin, "env.init", "-p", version)
        result = pytester.run(*poetry_bin, "run", "python", "--version")
        assert version in result.outlines[0]

    def test_remove_should_delete_the_specified_env(self, pytester, inv_bin):
        """Env operation remove should delete the specified env."""
        pytester.run(*inv_bin, "env.init")

        venvs_folder = self.test_root / ".venvs"
        venv_folder = next(venvs_folder.glob("./test*py" + self.versions[0]))
        assert venv_folder.is_dir()
        assert (self.test_root / ".venv").is_symlink()

        pytester.run(*inv_bin, "env.remove", "-p", self.versions[0])

        assert not venv_folder.is_dir()
        assert not (self.test_root / ".venv").is_symlink()

    def test_use_should_create_the_needed_env(self, pytester, inv_bin):
        """Env operation use should create the needed env."""
        venvs_folder = self.test_root / ".venvs"
        symlink = self.test_root / ".venv"

        assert not list(venvs_folder.glob("./test*py" + self.versions[0]))
        assert not symlink.is_symlink()

        pytester.run(*inv_bin, "env", "-n")

        env_folder = next(venvs_folder.glob("./test*py" + self.versions[0]))
        assert env_folder.is_dir()
        assert not symlink.is_symlink()

        pytester.run(*inv_bin, "env.use", "-p", self.versions[-1])

        env_folder = next(venvs_folder.glob("./test*py" + self.versions[-1]))
        assert env_folder.is_dir()
        assert symlink.is_symlink()
        assert symlink.resolve() == env_folder

    def test_init_should_be_able_to_use_a_custom_install_function(
        self, pytester, inv_bin, poetry_bin_str, add_test_file
    ):
        """Env operation init should be able to use a custom installation function."""
        versions = self.versions
        # language=python prefix="versions=[] if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns
            from pathlib import Path
            
            # noinspection PyUnusedLocal
            def installer(c, quiet):
                Path("./test_file").touch()
                
            ns, task = init_ns(
                "{versions[0]}", 
                {versions},
                poetry_bin="{poetry_bin_str}",
                install_project_dependencies_hook=installer)
            """
        add_test_file(source=task_source, debug_mode=False)

        assert not (self.test_root / "test_file").is_file()
        pytester.run(*inv_bin, "env.init", "-p", self.versions[0])
        assert (self.test_root / "test_file").is_file()
