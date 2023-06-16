import pytest
from _pytest.config import ExitCode


class TestACollectionDecorator:
    """Test: A CollectionDecorator..."""

    task_source: str

    @pytest.fixture(autouse=True)
    def setup(self, request, add_test_file, poetry_bin_str):
        """TestEnvOperation single test setup"""
        # language=python prefix="if True:" # IDE language injection
        task_source = f"""
            from typing import Optional
            from invoke import Collection, Context, Result  # type: ignore[attr-defined]
            from invoke_poetry.decorator import CollectionDecorator
            
            ns = Collection()
            ds = Collection("docs")
            ns.add_collection(ds)
            doc_task = CollectionDecorator(ds).decorator
            
            @doc_task
            def docs_a(c: Context) -> Optional[Result]:
                return c.run("echo 'a'")
            
            @doc_task(default=True)
            def docs_b(c: Context, version: str = "") -> Optional[Result]:
                return c.run(f"echo 'b{{version}}'")
            """
        add_test_file(source=task_source, debug_mode=False)
        request.cls.task_source = task_source

    def test_should_allow_to_easily_decorate_and_register_a_function(
        self, pytester, inv_bin, add_test_file
    ):
        """A CollectionDecorator should allow to easily decorate and register a function."""
        # check if the tasks are available
        result = pytester.run(*inv_bin, "-l")
        result.stdout.re_match_lines(
            [r"Available tasks:", r".*docs\.docs-a", r".*docs\.docs-b\ \(docs\)"]
        )
        # actually run the tasks
        result = pytester.run(*inv_bin, "docs.docs-a")
        result.stdout.re_match_lines([r"a"])
        result = pytester.run(*inv_bin, "docs", "-v", "42")
        result.stdout.re_match_lines([r"b42"])

    @pytest.mark.slow
    def test_should_result_in_correct_type_hints_all_around(
        self, pytester, inv_bin, poetry_bin, mypy_bin, add_test_file
    ):
        """A CollectionDecorator should result in correct type hints all around."""

        # !ADD the following source to the self.task_source!

        # language=python prefix="doc_task, docs_a, docs_b = lambda: None ns, CollectionDecorator, Collection, Context = None if True:" # noqa
        task_source = f"""
            import sys
            
            if sys.version_info < (3, 11):
                from typing_extensions import reveal_type
            else:
                from typing import reveal_type
            from invoke_poetry import cast_to_task_type
            from invoke_poetry.decorator import OverloadedDecoratorType
                
            def get_decorator(collection: Collection) -> OverloadedDecoratorType:
                return CollectionDecorator(collection).decorator
                
            ts = Collection("types")
            ns.add_collection(ts)
            type_task = get_decorator(ts)
            
            @type_task
            def types_a(c: Context) -> int:
                reveal_type(docs_a)
                reveal_type(docs_b)
                return 42
                
            @type_task(default=True)
            def types_b(c: Context) -> str:
                return "42" 
                
            reveal_type(types_a)
            reveal_type(types_b)
            reveal_type(cast_to_task_type(types_a))
            """
        add_test_file(source=self.task_source + task_source, debug_mode=False)

        # Check the runtime type (reveal_type prints to stderr!)
        result = pytester.run(*inv_bin, "types.types-a")
        result.stderr.re_match_lines(
            [
                r"Runtime type is 'Task'",
                r"Runtime type is 'Task'",
                r"Runtime type is 'Task'",
                r"Runtime type is 'Task'",
                r"Runtime type is 'Task'",
            ]
        )

        # Install and run mypy (VERY SLOW!!!)
        pytester.run(*poetry_bin, "run", "pip", "install", "mypy")
        result = pytester.run(*mypy_bin, "--strict", "tasks.py")
        result.stdout.re_match_lines(
            [
                # def (c: invoke.context.Context) -> Union[invoke.runners.Result, None]
                r".*note\:\ Revealed\ type\ is\ \"def\ \(c\:\ invoke\.context\.Context\)\ "
                r"\-\>\ Union\[invoke\.runners\.Result\,\ None\]\"",
                # def (c: invoke.context.Context, version: builtins.str =) -> Union[invoke.runners.Result, None]
                r".*note\:\ Revealed\ type\ is\ \"def\ \(c\:\ invoke\.context\.Context\,\ version\:"
                r"\ builtins\.str\ \=\)\ \-\>\ Union\[invoke\.runners\.Result\,\ None\]\"",
                # def (c: invoke.context.Context) -> builtins.int
                r".*note\:\ Revealed\ type\ is\ \"def\ \(c\:\ invoke\.context\.Context\)\ \-\>\ builtins\.int\"",
                # def (c: invoke.context.Context) -> builtins.str
                r".*note\:\ Revealed\ type\ is\ \"def\ \(c\:\ invoke\.context\.Context\)\ \-\>\ builtins\.str\"",
                # invoke.tasks.Task[def (c: invoke.context.Context) -> builtins.int]
                r".*note\:\ Revealed\ type\ is\ \"invoke\.tasks\.Task\[def\ \(c\:\ invoke\.context\.Context\)"
                r"\ \-\>\ builtins\.int\]\"",
            ]
        )
        assert result.ret == ExitCode.OK
