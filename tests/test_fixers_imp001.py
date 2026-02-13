"""Tests for IMP001 fixer: Move local imports to module level."""
from __future__ import annotations

import textwrap

from pyguard.fixers.imp001 import fix_local_imports


class TestFixBasicMove:
    def test_simple_import(self) -> None:
        source: str = textwrap.dedent("""\
            def f() -> None:
                import json
                json.loads("{}")
        """)
        expected: str = textwrap.dedent("""\
            import json

            def f() -> None:
                json.loads("{}")
        """)
        assert fix_local_imports(source) == expected

    def test_from_import(self) -> None:
        source: str = textwrap.dedent("""\
            def f() -> str:
                from pathlib import Path
                return str(Path.cwd())
        """)
        expected: str = textwrap.dedent("""\
            from pathlib import Path

            def f() -> str:
                return str(Path.cwd())
        """)
        assert fix_local_imports(source) == expected

    def test_multiple_imports(self) -> None:
        source: str = textwrap.dedent("""\
            def f() -> str:
                import json
                import re
                return re.sub(r"x", "", json.dumps({}))
        """)
        expected: str = textwrap.dedent("""\
            import json
            import re

            def f() -> str:
                return re.sub(r"x", "", json.dumps({}))
        """)
        assert fix_local_imports(source) == expected

    def test_method_import(self) -> None:
        source: str = textwrap.dedent("""\
            class C:
                def m(self) -> None:
                    import json
                    json.loads("{}")
        """)
        expected: str = textwrap.dedent("""\
            import json

            class C:
                def m(self) -> None:
                    json.loads("{}")
        """)
        assert fix_local_imports(source) == expected


class TestFixDuplicateRemoval:
    def test_already_at_module_level(self) -> None:
        source: str = textwrap.dedent("""\
            import json

            def f() -> None:
                import json
                json.loads("{}")
        """)
        expected: str = textwrap.dedent("""\
            import json

            def f() -> None:
                json.loads("{}")
        """)
        assert fix_local_imports(source) == expected


class TestFixConditionalSkip:
    def test_try_except_import_error_no_change(self) -> None:
        source: str = textwrap.dedent("""\
            def f() -> None:
                try:
                    import ujson as json
                except ImportError:
                    import json
                json.loads("{}")
        """)
        assert fix_local_imports(source) == source


class TestFixImportOrdering:
    def test_stdlib_before_third_party(self) -> None:
        source: str = textwrap.dedent("""\
            from myapp.utils import helper

            def f() -> None:
                import json
                json.loads("{}")
        """)
        expected: str = textwrap.dedent("""\
            import json

            from myapp.utils import helper

            def f() -> None:
                json.loads("{}")
        """)
        assert fix_local_imports(source) == expected


class TestFixNoChange:
    def test_no_local_imports(self) -> None:
        source: str = "import json\n\ndef f() -> None:\n    json.loads('{}')\n"
        assert fix_local_imports(source) == source

    def test_empty_source(self) -> None:
        assert fix_local_imports("") == ""

    def test_syntax_error(self) -> None:
        source: str = "def f(\n"
        assert fix_local_imports(source) == source


class TestFixEdgeCases:
    def test_async_function(self) -> None:
        source: str = textwrap.dedent("""\
            async def f() -> None:
                import json
                json.loads("{}")
        """)
        expected: str = textwrap.dedent("""\
            import json

            async def f() -> None:
                json.loads("{}")
        """)
        assert fix_local_imports(source) == expected

    def test_nested_function(self) -> None:
        source: str = textwrap.dedent("""\
            def outer() -> str:
                def inner() -> str:
                    import os
                    return os.getcwd()
                return inner()
        """)
        expected: str = textwrap.dedent("""\
            import os

            def outer() -> str:
                def inner() -> str:
                    return os.getcwd()
                return inner()
        """)
        assert fix_local_imports(source) == expected
