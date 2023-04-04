from _pytest.config import ExitCode


class TestATaskMatrix:
    """Test: A task matrix..."""

    task_names = ["task_a", "task_b", "task_c", "task_d"]

    def test_should_pass_all_arguments_to_the_hook(
        self, pytester, inv_bin, add_test_file
    ):
        """A task matrix should pass all arguments to the hook."""

        names = str(self.task_names)

        # language=python prefix="names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(c: Runner, name: str, tag: str):
                c.run(f"echo 'name: {{name}} {{tag}}'")
                    
            @task(name="matrix")
            def test_task(c):
                task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{'tag': "TAG"}}),
                    task_names={names},
                )
            """
        add_test_file(source=task_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "matrix")
        result.stdout.re_match_lines([f"name: {name} TAG" for name in self.task_names])

    def test_should_return_a_report_of_the_run(self, pytester, add_test_file, inv_bin):
        """A task matrix should return a report of the run."""

        names = str(self.task_names)

        # language=python prefix="names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(c: Runner, name: str, tag: str):
                c.run(f"echo 'name: {{name}} {{tag}}'")
                    
            @task(name="matrix")
            def test_task(c):
                result = task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{'tag': "TAG"}}),
                    task_names={names},
                )
                result.print_report()
            """
        add_test_file(source=task_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "matrix")
        result.stdout.re_match_lines([f".*{name}:.*OK" for name in self.task_names])

    def test_should_exit_with_an_error_if_a_task_errors_out(
        self, pytester, inv_bin, add_test_file
    ):
        """A task matrix should exit with an error if a task errors out."""

        names = str(self.task_names)

        # language=python prefix="names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(_: Runner, __: str, ___: str):
                raise Exception
                    
            @task(name="matrix")
            def test_task(c):
                result = task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{'tag': "TAG"}}),
                    task_names={names},
                )
                result.print_report()
                result.exit_with_rc()
            """
        add_test_file(source=task_source, debug_mode=False)

        # actually run the task
        result = pytester.run(*inv_bin, "matrix")
        assert result.ret == ExitCode.TESTS_FAILED

    def test_should_be_able_to_interrupt_a_run_when_a_user_send_a_sigint(
        self, pytester, inv_bin, add_test_file
    ):
        """A task matrix should be able to interrupt a run when a user send a sigint."""

        names = str(self.task_names)

        # language=python prefix="names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(c: Runner, name: str, tag: str):
                if name == "task_b":
                    import os
                    import signal 
                    # simulate a sigint from the outside
                    os.kill(os.getpid(), signal.SIGINT)
                c.run(f"echo 'name: {{name}} {{tag}}'")
                    
            @task(name="matrix")
            def test_task(c):
                result = task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{'tag': "TAG"}}),
                    task_names={names},
                )
                result.print_report()
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "matrix")
        result.stdout.re_match_lines(
            [
                ".*task_a:.*OK",
                ".*task_b:.*INTERRUPTED",
                ".*task_c:.*SKIPPED",
                ".*task_d:.*SKIPPED",
            ]
        )

    def test_should_keep_going_if_a_task_fails(self, pytester, inv_bin, add_test_file):
        """A task matrix should keep going if a task fails."""

        names = str(self.task_names)

        # language=python prefix="names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(c: Runner, name: str, tag: str):
                if name == "task_b":
                    raise Exception
                c.run(f"echo 'name: {{name}} {{tag}}'")
                    
            @task(name="matrix")
            def test_task(c):
                result = task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{'tag': "TAG"}}),
                    task_names={names},
                )
                result.print_report()
            """
        add_test_file(source=task_source, debug_mode=False)
        result = pytester.run(*inv_bin, "matrix")
        result.stdout.re_match_lines(
            [
                ".*task_a:.*OK",
                ".*task_b:.*FAILED",
                ".*task_c:.*OK",
                ".*task_d:.*OK",
            ]
        )

    def test_should_try_to_maintain_the_active_poetry_env(
        self, pytester, inv_bin, add_test_file, poetry_bin_str, poetry_bin
    ):
        """A task matrix should try to maintain the active poetry env."""

        task_names = ["3.8", "3.9"]
        names = str(task_names)

        # language=python prefix="poetry_bin_str='';names=('')\nif True:" # IDE language injection
        task_source = f"""
            from invoke import Runner
            from invoke_poetry import init_ns, task_matrix
            
            ns, task = init_ns("3.8")
            
            def my_hook(c: Runner, name: str):
                c.run(f"{poetry_bin_str} env use {{name}}")
                    
            @task(name="matrix")
            def test_task(c):
                result = task_matrix(
                    hook=my_hook,
                    hook_args_builder=lambda name: ([c, name],{{}}),
                    task_names={names},
                )
                result.print_report()
            """
        add_test_file(source=task_source, debug_mode=False)
        pytester.run(*poetry_bin, "env", "use", "3.8")
        result = pytester.run(*inv_bin, "matrix")
        assert result.ret == ExitCode.OK
        result = pytester.run(*poetry_bin, "env", "info", "-p")
        result.stdout.re_match_lines([r"\.venvs\/.*py3.8"])
