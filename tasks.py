from invoke import task

from invoke_poetry import Verbose, env_use, install_project_dependencies


@task
def init(c):
    c.run("poetry env use python3.7")
    c.run("poetry install")
    c.run("rm -f .venv && ln -s `poetry env info -p` .venv")


@task
def test(c):
    c.run("poetry run pytest")


@task
def test_cov(c):
    c.run("poetry run pytest --cov=invoke_poetry --cov-report html:coverage/cov_html")
    c.run("xdg-open coverage/cov_html/index.html")


@task
def tt(c):
    install_project_dependencies(c, verbose=True)
