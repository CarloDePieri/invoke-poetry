from _pytest.config import ExitCode


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
