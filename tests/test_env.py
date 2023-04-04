from _pytest.config import ExitCode


class TestRememberActiveEnv:
    """Test: remember_active_env..."""

    def test_should_go_back_to_the_previous_poetry_env(
        self, pytester, inv_bin, add_test_file, poetry_bin_str
    ):
        """Remember active env should go back to the previous poetry env."""
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
        """Remember active env should not change back the env if no poetry env was active before."""
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
