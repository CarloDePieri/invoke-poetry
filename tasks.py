from typing import Optional

from invoke import Result, Runner  # type: ignore[attr-defined]

from invoke_poetry import (
    TaskMatrix,
    add_sub_collection,
    get_additional_args_string,
    init_ns,
    poetry_venv,
    task_matrix,
)
from invoke_poetry.logs import error

supported_python_versions = ["3.8", "3.9", "3.10", "3.11"]
default_python_version = supported_python_versions[0]

coverage_report_folder = "coverage/cov_html"
project_folder = "invoke_poetry"
test_folder = "tests"


ns, task = init_ns(
    default_python_version=default_python_version,
    supported_python_versions=supported_python_versions,
)
test_collection, task_t = add_sub_collection(ns, "test")
_, task_c = add_sub_collection(test_collection, "coverage")
_, task_p = add_sub_collection(ns, "publish")


#
# LINTING AND FORMATTING
#
@task
def checks(c: Runner, _filter: Optional[str] = None):
    """Run several formatting, linting and static type checks.

    A subset of checks to perform can be specified with the `filter` flag as a list of names separated
    by a comma (e.g. mypy,black).
    """
    checklist = {
        "black": f"black --check {project_folder} {test_folder} tasks.py",
        "isort": f"isort --check {project_folder} {test_folder} tasks.py",
        "flake8": f"flake8 {project_folder}",
        "mypy": f"mypy --strict --no-error-summary {project_folder}",
    }

    if _filter:
        try:
            checklist = dict((name, checklist[name]) for name in _filter.split(","))
        except KeyError as name:
            error(
                f"{name} is not a valid check! Choose from: {', '.join(checklist.keys())}"
            )

    with poetry_venv(c):
        results = task_matrix(
            hook=c.run,
            hook_args_builder=lambda name: (
                [checklist[name]],
                {"pty": True},
            ),
            task_names=checklist.keys(),
            print_steps=True,
        )
        results.print_report()
        results.exit_with_rc()
        return results


#
# TESTS
#
@task_t(name="dev", default=True)
def test_dev(
    c: Runner, python_version: Optional[str] = None, rollback_env: bool = True
) -> Result:
    """Launch all tests. Remember to launch `inv env.init --all` once, first."""
    with poetry_venv(c, python_version=python_version, rollback_env=rollback_env):
        # This allows to pass additional parameter to pytest like this: inv test -- -m 'not slow'
        command = "pytest" + get_additional_args_string()
        result = c.run(command)
    return result


@task_t(name="matrix")
def test_matrix(c: Runner) -> TaskMatrix:
    """Launch the test suite with all supported python version."""
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
    return results


#
# TESTS COVERAGE
#
@task_c(name="run_tests", default=True)
def test_cov(
    c: Runner,
    python_version: Optional[str] = None,
    rollback_env: bool = True,
    open_report: bool = True,
) -> Result:
    """Launch the test suite and produce a coverage report."""
    with poetry_venv(c, python_version=python_version, rollback_env=rollback_env):
        result = c.run(
            f"pytest --cov=invoke_poetry --cov-report html:{coverage_report_folder}{get_additional_args_string()}"
        )
        if open_report:
            test_cov_report(c)
    return result


@task_c(name="open_report")
def test_cov_report(c: Runner) -> Result:
    """Open the latest coverage report."""
    return c.run(f"xdg-open {coverage_report_folder}/index.html")


#
# PYPI
#
@task(name="build")
def build(c: Runner) -> Result:
    """Build the project with poetry. Artifact will be produced in the dist/ folder. This is needed to publish on
    pypi."""
    return c.run("poetry build")


@task_p(name="pypi", default=True)
def publish(c: Runner) -> Result:
    """Publish the project on pypi with poetry. A project build is needed first."""
    return c.run("poetry publish")


@task_p(name="pypi_test")
def publish_test(c: Runner) -> Result:
    """Publish the project on testing pypi repository with poetry. A project build is needed first."""
    return c.run("poetry publish -r testpypi")


#
# ACT
#
