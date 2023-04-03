from _pytest.config import ExitCode


class TestACollection:
    """Test: A Collection..."""

    def test_should_allow_to_easily_add_tasks(self, pytester, inv_bin, add_test_file):
        """A collection should allow to easily add tasks."""

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
        """A collection should allow to add sub-collections and relative tasks."""

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

    def test_should_not_freak_out_if_type_annotations_are_present(
        self, pytester, inv_bin, add_test_file
    ):
        """A collection should not freak out if type annotations are present."""

        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns
            from typing import Optional
            
            ns, task = init_ns("3.8")
            
            @task
            def annotated(c: Runner, python_version: Optional[str] = None) -> Optional[str]:
                if python_version:
                    c.run(f"echo 'python {{python_version}}'")
                else:
                    c.run("echo 'No python for you!'")
                return python_version
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "annotated", "-p", "3.9")
        assert result.ret == ExitCode.OK
        result.stdout.re_match_lines(["python 3.9"])
