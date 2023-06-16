from typing import Optional

from invoke import Context, Result  # type: ignore[attr-defined]

from invoke_poetry import (
    TaskMatrix,
    add_sub_collection,
    get_additional_args_string,
    init_ns,
    poetry_runner,
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
# LINTING, FORMATTING AND TYPE CHECKING
#
@task
def checks(
    c: Context,
    _filter: Optional[str] = None,
    python_version: str = default_python_version,
) -> TaskMatrix:
    """Run several formatting, linting and static type checks.

    A subset of checks to perform can be specified with the `--filter` flag as a list of names separated
    by a comma (e.g. mypy,black).
    By default the checks are launched in the dev environment; if needed, a different one can be specified by the
    `--python-version` flag.
    """
    checklist = {
        "black": f"black --check {project_folder} {test_folder} tasks.py",
        "isort": f"isort --check {project_folder} {test_folder} tasks.py",
        "flake8": f"flake8 {project_folder}",
        "mypy": f"mypy {project_folder} tasks.py",
    }

    if _filter:
        try:
            checklist = dict((name, checklist[name]) for name in _filter.split(","))
        except KeyError as name:
            error(
                f"{name} is not a valid check! Choose from: {', '.join(checklist.keys())}"
            )

    with poetry_runner(c, python_env=python_version) as run:
        results = task_matrix(
            hook=run,
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
    c: Context, python_version: Optional[str] = None, rollback_env: bool = True
) -> Optional[Result]:
    """Launch all tests. Remember to launch `inv env.init --all` once, first."""
    with poetry_runner(c, python_env=python_version, rollback_env=rollback_env) as run:
        # This allows to pass additional parameter to pytest like this: inv test -- -m 'not slow'
        command = "pytest" + get_additional_args_string()
        result = run(command)
    return result


@task_t(name="matrix")
def test_matrix(c: Context) -> TaskMatrix:
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
    c: Context,
    python_version: Optional[str] = None,
    rollback_env: bool = True,
    open_report: bool = True,
) -> Optional[Result]:
    """Launch the test suite and produce a coverage report."""
    with poetry_runner(c, python_env=python_version, rollback_env=rollback_env) as run:
        result = run(
            f"pytest --cov=invoke_poetry --cov-report html:{coverage_report_folder}{get_additional_args_string()}"
        )
        if open_report:
            test_cov_report(c)
    return result


@task_c(name="open_report")
def test_cov_report(c: Context) -> Optional[Result]:
    """Open the latest coverage report."""
    return c.run(f"xdg-open {coverage_report_folder}/index.html")


#
# PYPI
#
@task(name="build")
def build(c: Context) -> Optional[Result]:
    """Build the project with poetry. Artifact will be produced in the dist/ folder. This is needed to publish on
    pypi."""
    return c.run("poetry build")


@task_p(name="pypi", default=True)
def publish(c: Context) -> Optional[Result]:
    """Publish the project on pypi with poetry. A project build is needed first."""
    return c.run("poetry publish")


@task_p(name="pypi_test")
def publish_test(c: Context) -> Optional[Result]:
    """Publish the project on testing pypi repository with poetry. A project build is needed first."""
    return c.run("poetry publish -r testpypi")


#
# ACT
#
