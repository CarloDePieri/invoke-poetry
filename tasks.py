from time import sleep
from typing import Optional

from invoke import Result, Runner

from invoke_poetry import add_sub_collection, init_ns, poetry_venv, task_matrix

supported_python_versions = ["3.7", "3.8", "3.9", "3.10"]
default_python_version = supported_python_versions[0]


ns, task = init_ns(
    default_python_version=default_python_version,
    supported_python_versions=supported_python_versions,
)
tc, task_t = add_sub_collection(ns, "test")


@task
def tt(c: Runner) -> None:
    c.run("echo yo")


@task_t(name="dev", default=True)
def test_dev(
    c: Runner, python_version: Optional[str] = None, rollback_env: bool = True
) -> Result:
    """Launch all tests. Remember to launch `inv env.init --all` once, first."""
    with poetry_venv(c, python_version=python_version, rollback_env=rollback_env):
        # print("wait")
        # sleep(10)
        result = c.run("python --version")
    return result


@task_t(name="matrix")
def test_matrix(c: Runner) -> None:
    """TODO"""
    results = task_matrix(
        hook=test_dev,
        hook_args_builder=lambda name: (
            [c],
            {"python_version": name, "rollback_env": False},
        ),
        task_names=reversed(supported_python_versions),
        print_steps=True,
    )
    results.print_report()
    results.exit_with_rc()


# from invoke_poetry import (
#     Collection,
#     Settings,
#     init_collection,
#     install_project_dependencies,
#     poetry_venv,
#     pr,
#     task_in_poetry_env_matrix,
# )

# supported_python_versions = ["3.7", "3.8", "3.9", "3.10"]
# dev_python_version = supported_python_versions[0]

# ns = Collection()
# Settings.init(ns, dev_python_version, supported_python_versions)

# @ns.task
# def init(c):
#     with poetry_venv(c):
#         install_project_dependencies(c)
#
#
# test_coll = Collection("test")
# ns.add_collection(test_coll)
#
#
# @test_coll.task(name="dev", default=True)
# def test(c, python_version=dev_python_version):
#     with poetry_venv(c, python_version=python_version):
#         install_project_dependencies(c)
#         pr("pytest", c)
#
#
# @test_coll.task(name="matrix")
# @task_in_poetry_env_matrix(python_versions=supported_python_versions)
# def test_matrix(c):
#     install_project_dependencies(c)
#     pr("pytest", c)
#
#
# @test_coll.task(name="cov")
# def test_cov(c):
#     with poetry_venv(c):
#         install_project_dependencies(c)
#         pr("pytest --cov=invoke_poetry --cov-report html:coverage/cov_html", c)
#         pr("xdg-open coverage/cov_html/index.html", c)
