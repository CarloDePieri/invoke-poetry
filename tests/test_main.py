from _pytest.config import ExitCode


class TestPoetryRunner:
    """Test: poetry_runner..."""

    def test_should_allow_to_switch_poetry_venv(
        self,
        pytester,
        inv_bin,
        add_test_file,
        poetry_bin_str,
    ):
        """poetry_runner should allow to switch poetry venv."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from pathlib import Path
            from invoke_poetry import init_ns, poetry_runner
            from typing import Callable, Optional
            from invoke import Result
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
            
            def get_python_bin(run: Callable[..., Optional[Result]], cmd: str) -> Path:
               return Path(run(cmd).stdout.rstrip("\\n")).absolute().resolve()
               
            @task()
            def test(c):
                outside_python_bin = get_python_bin(c.run, "which python")
                with poetry_runner(c, python_env="3.9") as run:
                    inside_python_bin = get_python_bin(run, "which python")
                    assert "3.9" in inside_python_bin.name
                    assert inside_python_bin != outside_python_bin
                # since there were no active poetry env before, the 3.9 should stay active
                assert inside_python_bin == get_python_bin(c.run, "{poetry_bin_str} run which python") 
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_go_back_to_a_previously_active_poetry_runner_after_execution(
        self, pytester, inv_bin, poetry_bin_str, add_test_file
    ):
        """poetry_runner should go back to a previously active poetry env after execution."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from pathlib import Path
            from typing import Callable, Optional
            from invoke import Result
            from invoke_poetry import init_ns, poetry_runner
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
            
            def get_python_bin(run: Callable[..., Optional[Result]], cmd: str) -> Path:
               return Path(run(cmd).stdout.rstrip("\\n")).absolute().resolve()
               
            @task()
            def test(c):
                outside_python_bin = get_python_bin(c.run, "which python")
                c.run("{poetry_bin_str} env use 3.8")
                previously_active_poetry_python = get_python_bin(c.run, "{poetry_bin_str} run which python")
                with poetry_runner(c, python_env="3.9") as run:
                    inside_python_bin = get_python_bin(run, "which python")
                    assert "3.9" in inside_python_bin.name
                    assert inside_python_bin != outside_python_bin
                    assert inside_python_bin != previously_active_poetry_python
                # since there were an active poetry env before, it should have gone back to it
                assert previously_active_poetry_python == get_python_bin(c.run, "{poetry_bin_str} run which python") 
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_only_activate_the_env_if_starting_from_a_different_one(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """Poetry runner should only activate the env if starting from a different one."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, poetry_runner
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
               
            @task()
            def test(c):
                c.run("{poetry_bin_str} env use 3.8")
                with poetry_runner(c, python_env="3.8", quiet=False):
                    pass
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK
        result.stdout.no_re_match_line(r".*Activated\ env:\ 3\.8")

    def test_should_patch_the_runner(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """poetry_runner should patch the runner."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, poetry_runner
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
            
            @task()
            def test(c):
                with poetry_runner(c, python_env="3.8", quiet=False) as run:
                    result = run("echo ''")
                    assert "{poetry_bin_str}" in result.command
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK


class TestAnyAdditionalArgs:
    """Test: AnyAdditionalArgs..."""

    def test_should_be_handled_as_a_list(self, pytester, inv_bin, add_test_file):
        """Any additional args should be handled as a list."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, get_additional_args
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])
            
            @task()
            def test(_):
                print(get_additional_args())
            """
        add_test_file(source=task_source, debug_mode=False)
        additional_args = ["-c", "command", "-m", "something with spaces"]
        result = pytester.run(*inv_bin, "test", "--", *additional_args)
        assert result.ret == ExitCode.OK
        # should output the string: "['-c', 'command', '-m', 'something with spaces']"
        assert result.outlines == [
            "[" + ", ".join(f"'{x}'" for x in additional_args) + "]"
        ]

    def test_should_be_handled_as_a_string(self, pytester, inv_bin, add_test_file):
        """Any additional args should be handled as a string."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, get_additional_args_string
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])

            @task()
            def test(_):
                print(get_additional_args_string())
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(
            *inv_bin, "test", "--", "-c", "command", "-m", "something with spaces"
        )
        assert result.ret == ExitCode.OK
        assert result.outlines == [' -c command -m "something with spaces"']

    def test_should_be_handled_when_empty(self, pytester, inv_bin, add_test_file):
        """Any additional args should be handled when empty."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, get_additional_args_string
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"])

            @task()
            def test(_):
                print(get_additional_args_string())
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test", "--")
        assert result.ret == ExitCode.OK
        assert result.outlines == [""]
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK
        assert result.outlines == [""]


class TestCollectionHandlers:
    """Test: CollectionHandlers..."""

    def test_should_allow_to_easily_add_tasks(self, pytester, inv_bin, add_test_file):
        """Collection handlers should allow to easily add tasks."""
        task_name = "hello"
        task_out = "hi!"

        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns
            
            ns, task = init_ns("3.8")
            
            @task(name="{task_name}")
            def test_task(c):
                c.run("echo '{task_out}'")
            """
        add_test_file(source=task_source, debug_mode=False)

        # check that the task is available
        result = pytester.run(*inv_bin, "-l")
        result.stdout.re_match_lines([r"Available tasks:", r".*" + task_name])

        # actually run the task
        result = pytester.run(*inv_bin, task_name)
        result.stdout.re_match_lines([r"" + task_out])

    def test_should_allow_to_add_sub_collections_and_relative_tasks(
        self, pytester, inv_bin, add_test_file
    ):
        """Collection handlers should allow to add sub-collections and relative tasks."""
        collection = "test"
        name = "matrix"
        task_name = f"{collection}.{name}"
        out = "Hello world!"

        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke_poetry import init_ns, add_sub_collection
            
            ns, task = init_ns("3.8")
            test, taskt = add_sub_collection(ns, "{collection}")
            
            @taskt(name="{name}")
            def test_task(c):
                c.run("echo '{out}'")
            """
        add_test_file(source=task_source, debug_mode=False)

        # check that the task is available
        result = pytester.run(*inv_bin, "-l")
        result.stdout.re_match_lines([r"Available tasks:", r".*" + task_name])

        # actually run the task
        result = pytester.run(*inv_bin, task_name)
        result.stdout.re_match_lines([out])
