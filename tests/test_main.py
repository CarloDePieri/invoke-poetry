from _pytest.config import ExitCode


class TestPoetryEnv:
    """Test: poetry_env..."""

    def test_should_allow_to_switch_poetry_venv(
        self,
        pytester,
        inv_bin,
        add_test_file,
        poetry_bin_str,
    ):
        """poetry_env should allow to switch poetry venv."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from pathlib import Path
            from invoke.runners import Runner
            from invoke_poetry import init_ns, poetry_venv
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
            
            def get_python_bin(c: Runner, cmd: str) -> Path:
               return Path(c.run(cmd).stdout.rstrip("\\n")).absolute().resolve()
               
            @ns.task()
            def test(c):
                outside_python_bin = get_python_bin(c, "which python")
                with poetry_venv(c, python_version="3.9", rollback_env=True):
                    inside_python_bin = get_python_bin(c, "which python")
                    assert "3.9" in inside_python_bin.name
                    assert inside_python_bin != outside_python_bin
                # since there were no active poetry env before, the 3.9 should stay active
                assert inside_python_bin == get_python_bin(c, "{poetry_bin_str} run which python") 
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "test")
        assert result.ret == ExitCode.OK

    def test_should_go_back_to_a_previously_active_poetry_env_after_execution(
        self, pytester, inv_bin, poetry_bin_str, add_test_file
    ):
        """poetry_env should go back to a previously active poetry env after execution."""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from pathlib import Path
            from invoke.runners import Runner
            from invoke_poetry import init_ns, poetry_venv
            
            ns, task = init_ns("3.8", supported_python_versions=["3.8", "3.9"], poetry_bin="{poetry_bin_str}")
            
            def get_python_bin(c: Runner, cmd: str) -> Path:
               return Path(c.run(cmd).stdout.rstrip("\\n")).absolute().resolve()
               
            @ns.task()
            def test(c):
                outside_python_bin = get_python_bin(c, "which python")
                c.run("{poetry_bin_str} env use 3.8")
                previously_active_poetry_python = get_python_bin(c, "{poetry_bin_str} run which python")
                with poetry_venv(c, python_version="3.9", rollback_env=True):
                    inside_python_bin = get_python_bin(c, "which python")
                    assert "3.9" in inside_python_bin.name
                    assert inside_python_bin != outside_python_bin
                    assert inside_python_bin != previously_active_poetry_python
                # since there were an active poetry env before, it should have gone back to it
                assert previously_active_poetry_python == get_python_bin(c, "{poetry_bin_str} run which python") 
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
            
            @ns.task()
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

            @ns.task()
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

            @ns.task()
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
