from pathlib import Path
from _pytest.config import ExitCode


class TestACollection:
    """Test: A Collection..."""

    def test_should_allow_to_easily_add_tasks(self, pytester, inv):
        """A collection should allow to easily add tasks."""

        task_name = "hello"
        task_out = "hi!"

        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import Collection
            
            ns = Collection()
            
            @ns.task(name="{task_name}")
            def test_task(c):
                c.run("echo '{task_out}'")
            """
        pytester.makepyfile(tasks=task_source)

        result = pytester.run(inv, "-l")
        result.stdout.re_match_lines([r"Available tasks:", r".*" + task_name])

        result = pytester.run(inv, task_name)
        result.stdout.re_match_lines([r"" + task_out])


class TestEnvUse:
    """Test: env_use..."""

    def test_should_allow_to_activate_an_env(self, pytester, inv):
        """env_use should allow to activate an env."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import env_use, task
            
            @task
            def env(c):
                env_use(c, '3.7')
            """
        pytester.makepyfile(tasks=task_source)

        pytester.run(inv, "env")

        result = pytester.run("poetry", "env", "info", "-p")

        poetry_venv = Path(result.outlines[0])
        venvs = Path(".venvs")
        venv = Path(".venv")

        assert venvs.is_dir()
        assert venvs.absolute() == poetry_venv.parent.absolute()
        assert venv.is_symlink()
        assert venv.resolve() == (venvs / poetry_venv.name).absolute()
        assert "3.7" in poetry_venv.name

    def test_should_have_a_default_python_version(self, pytester, inv):
        """env_use should have a default python version."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import env_use, Collection, Settings
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7'])
            
            @ns.task()
            def test(c):
                env_use(c)
            """
        pytester.makepyfile(tasks=task_source)

        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result = pytester.run("poetry", "env", "info", "-p")
        poetry_venv = Path(result.outlines[0])
        assert "3.7" in poetry_venv.name

    def test_without_a_proper_config_should_result_in_a_configuration_error(
        self, pytester, inv
    ):
        """Env use without a proper config should result in a configuration error."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import env_use, Collection
            
            ns = Collection()
            
            @ns.task()
            def test(c):
                env_use(c)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.TESTS_FAILED
        result.stdout.re_match_lines(r".*CONFIGURATION\ ERROR")


class TestPoetryVenv:
    """Test: poetry_venv..."""

    def test_should_allow_to_switch_env(self, pytester, inv, debugger):
        """poetry_venv should allow to switch env."""
        # language=python prefix="debugger=None\nif True:" # IDE language injection
        task_source = f"""
            {debugger(start=False)}
            from invoke_poetry import Collection, Settings, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    c.run("poetry run python --version")
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r"Python\ 3\.7.\d"])

        poetry_venv = pytester.run("poetry", "env", "info", "-p").outlines[0]
        assert Path(poetry_venv).is_dir()

    def test_should_restore_the_previous_env_after_it_s_done(
        self, pytester, inv, debugger
    ):
        """poetry_venv should restore the previous env after it's done."""
        # language=python prefix="debugger=None\nif True:" # IDE language injection
        task_source = f"""
            {debugger(start=False)}
            from invoke_poetry import Collection, Settings, poetry_venv, env_use, Verbose
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                env_use(c, verbose_level=Verbose.ZERO)  # this will set the env to 3.7
                with poetry_venv(c, '3.8'):
                    c.run("poetry run python --version")
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r"Python\ 3\.8.\d"])

        result = pytester.run("poetry", "run", "python", "--version")
        result.stdout.re_match_lines([r"Python\ 3\.7.\d"])

    def test_it_should_only_activate_an_env_if_necessary(self, pytester, inv, debugger):
        """poetry_venv it should only activate an env if necessary."""
        # language=python prefix="debugger=None\nif True:" # IDE language injection
        task_source = f"""
            {debugger(start=False)}
            from invoke_poetry import Collection, Settings, poetry_venv, env_use, Verbose
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                env_use(c, verbose_level=Verbose.ZERO)  # this will set the env to 3.7
                with poetry_venv(c, '3.7', verbose_level=Verbose.TWO):
                    c.run("poetry run python --version")
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.no_re_match_line(r"Using\ virtualenv.*")
        result.stdout.re_match_lines([r"Python\ 3\.7.\d"])


class TestProjectDependencies:
    """Test: Project dependencies..."""

    def test_can_be_installed_with_a_default_func(self, pytester, inv, debugger):
        """Project dependencies can be installed with a default func."""
        # language=python prefix="debugger=None\nif True:" # IDE language injection
        task_source = f"""
            {debugger(start=False)}
            from invoke_poetry import Collection, Settings, install_project_dependencies
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                install_project_dependencies(c)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
