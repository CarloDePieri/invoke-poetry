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

    def test_should_allow_to_switch_env(self, pytester, inv, debug):
        """poetry_venv should allow to switch env."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
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
        self, pytester, inv, debug
    ):
        """poetry_venv should restore the previous env after it's done."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
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

    def test_it_should_only_activate_an_env_if_necessary(self, pytester, inv, debug):
        """poetry_venv it should only activate an env if necessary."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
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

    def test_can_be_installed_with_a_default_func(self, pytester, inv, debug):
        """Project dependencies can be installed with a default func."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, install_project_dependencies, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    install_project_dependencies(c)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines(
            [
                r".*inv.*\ >\ poetry\ install",
                r".*Updating\ dependencies",
                r".*Writing\ lock\ file",
                r".*Installing",
            ]
        )

    def test_can_be_installed_silently(self, pytester, inv, debug):
        """Project dependencies can be installed silently."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, install_project_dependencies, Verbose, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    install_project_dependencies(c, verbose_level=Verbose.ZERO)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        assert result.outlines == []

    def test_can_be_installed_without_command_echo(self, pytester, inv, debug):
        """Project dependencies can be installed with command echo."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, install_project_dependencies, Verbose, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    install_project_dependencies(c, verbose_level=Verbose.ONE)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.no_re_match_line(r".*inv.*\ >\ poetry\ install")
        result.stdout.re_match_lines([r".*Updating\ dependencies"])

    def test_can_be_installed_with_a_custom_function(self, pytester, inv, debug):
        """Project dependencies can be installed with a custom function."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke import Runner
            from invoke_poetry import Collection, Settings, install_project_dependencies, Verbose, poetry_venv
            
            def custom(c: Runner, verbose_level: Verbose = Verbose.ONE):
                c.run(f"echo 'custom_install_command with verbosity {{verbose_level}}'")
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'], install_project_dependencies_hook=custom)
            
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    install_project_dependencies(c, verbose_level=Verbose.TWO)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines(
            [r"custom_install_command\ with\ verbosity\ Verbose\.TWO"]
        )


class TestAnyAdditionalArgs:
    """Test: AnyAdditionalArgs..."""

    def test_should_be_handled_as_a_list(self, pytester, inv, debug):
        """Any additional args should be handled as a list."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, get_additional_args
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                print(get_additional_args())
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(
            inv, "test", "--", "-c", "command", "-m", "something with spaces"
        )
        assert result.ret == ExitCode.OK
        assert result.outlines == ["['-c', 'command', '-m', 'something with spaces']"]

    def test_should_be_handled_as_a_string(self, pytester, inv, debug):
        """Any additional args should be handled as a string."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, get_additional_args_string
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                print(get_additional_args_string())
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(
            inv, "test", "--", "-c", "command", "-m", "something with spaces"
        )
        assert result.ret == ExitCode.OK
        assert result.outlines == [' -c command -m "something with spaces"']

    def test_should_be_handled_when_empty(self, pytester, inv, debug):
        """Any additional args should be handled when empty."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, get_additional_args_string
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                print(get_additional_args_string())
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test", "--")
        assert result.ret == ExitCode.OK
        assert result.outlines == [""]
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        assert result.outlines == [""]


class TestPoetryRun:
    """Test: poetry run..."""

    def test_should_execute_commands_inside_the_selected_environment(
        self, pytester, inv, debug
    ):
        """pr should execute commands inside the selected environment."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, pr, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    pr("python --version", c)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r".*\ poetry\ run\ python\ --version"])
        result.stdout.re_match_lines([r"Python\ 3\.7.\d"])

    def test_should_execute_commands_without_echoing_if_told(
        self, pytester, inv, debug
    ):
        """pr should execute commands without echoing if told."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, pr, Verbose, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    pr("python --version", c, verbose_level = Verbose.ONE)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.no_re_match_line(r".*\ poetry\ run\ python\ --version")
        result.stdout.re_match_lines([r"Python\ 3\.7.\d"])

    def test_should_execute_commands_silently_if_told(self, pytester, inv, debug):
        """pr should execute commands silently if told."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, pr, Verbose, poetry_venv
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task()
            def test(c):
                with poetry_venv(c, '3.7'):
                    pr("python --version", c, verbose_level = Verbose.ZERO)
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        assert not result.outlines


class TestATestMatrix:
    """Test: A test matrix..."""

    def test_should_execute_the_command_in_every_specified_env(
        self, pytester, inv, debug
    ):
        """A test matrix should execute the command in every specified env."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings, task_in_poetry_env_matrix
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            
            # noinspection PyUnusedLocal
            @ns.task(name="test")
            @task_in_poetry_env_matrix(python_versions=['3.7', '3.8'])
            def test(c):
                c.run("poetry run python --version")
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "test")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r"Python\ 3\.7.\d", r"Python\ 3\.8.\d"])


class TestEnvTasks:
    """Test: Env tasks..."""

    def test_should_be_able_to_change_env(self, pytester, inv, debug):
        """Env tasks should be able to change env."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "env.use", "-p", "3.8")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r"Using\ virtualenv"])
        result = pytester.run("poetry", "run", "python", "--version")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines([r"Python\ 3\.8.\d"])

    def test_should_be_able_to_list_available_env(self, pytester, inv, debug):
        """Env tasks should be able to list available env."""
        # language=python prefix="debug=None\nif True:" # IDE language injection
        task_source = f"""
            # noinspection PyStatementEffect,PyCallingNonCallable
            {debug(False)}
            from invoke_poetry import Collection, Settings
            
            ns = Collection()
            Settings.init(ns, '3.7', ['3.7', '3.8'])
            """
        pytester.makepyfile(tasks=task_source)
        result = pytester.run(inv, "env.list")
        assert result.ret == ExitCode.OK
        result.stdout.no_re_match_line(r".*test.*py")
        pytester.run(inv, "env.use", "-p", "3.7")
        pytester.run(inv, "env.use", "-p", "3.8")
        result = pytester.run(inv, "env.list")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines(
            [r".*test.*py3\.7", r".*test.*py3\.8\ \(Activated\)"]
        )
