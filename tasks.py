from invoke_poetry import (
    Collection,
    Settings,
    install_project_dependencies,
    poetry_venv,
    pr,
    task_in_poetry_env_matrix,
)

supported_python_versions = ["3.7", "3.8", "3.9", "3.10"]
dev_python_version = supported_python_versions[0]

ns = Collection()
Settings.init(ns, dev_python_version, supported_python_versions)


@ns.task
def init(c):
    with poetry_venv(c):
        install_project_dependencies(c)


test_coll = Collection("test")
ns.add_collection(test_coll)


@test_coll.task(name="dev", default=True)
def test(c, python_version=dev_python_version):
    with poetry_venv(c, python_version=python_version):
        install_project_dependencies(c)
        pr("pytest", c)


@test_coll.task(name="matrix")
@task_in_poetry_env_matrix(python_versions=supported_python_versions)
def test_matrix(c):
    install_project_dependencies(c)
    pr("pytest", c)


@test_coll.task(name="cov")
def test_cov(c):
    with poetry_venv(c):
        install_project_dependencies(c)
        pr("pytest --cov=invoke_poetry --cov-report html:coverage/cov_html", c)
        pr("xdg-open coverage/cov_html/index.html", c)
