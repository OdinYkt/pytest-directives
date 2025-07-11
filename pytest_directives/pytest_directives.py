import asyncio
import inspect
import logging
from asyncio import StreamReader
from pathlib import Path
from types import FunctionType, MethodType, ModuleType
from typing import Callable, TypeAlias, Union, Any

from ._pytest_hardcode import ExitCode
from .core.abc_directive import (
    ABCDirective,
    ABCRunnable,
    ABCRunStrategy,
    ABCTargetResolver,
    RunResult,
)
from .core.run_strategies import (
    ChainRunStrategy,
    ParallelRunStrategy,
    SequenceRunStrategy,
)

TestTargetType: TypeAlias = Union[ModuleType, FunctionType, MethodType, Callable[[Any], Any]]


class PytestRunnable(ABCRunnable):
    """Implement how need to run pytest tests from test_path"""
    def __init__(self, test_path: str):
        super().__init__()
        self._test_path = test_path


    async def run(self, *run_args: str) -> RunResult:
        """Run test item in another process, wait until done and collect results"""
        logging.debug(f"Run test from directive {self.__class__.__name__}: {self._test_path}")
        process = await asyncio.create_subprocess_exec(
            "pytest", self._test_path, *run_args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        process_stdout: list[str] = []
        process_stderr: list[str] = []

        await asyncio.gather(
            self.read_stream(process.stdout, process_stdout, logging.INFO),     # type: ignore[arg-type]
            self.read_stream(process.stderr, process_stderr, logging.INFO)      # type: ignore[arg-type]
        )

        await process.wait()

        if process.returncode != ExitCode.OK:
            is_ok = False
            logging.error("Errors in tests results")
        else:
            is_ok = True
            logging.debug("Tests ends without errors")
        return RunResult(is_ok=is_ok, stdout=process_stdout, stderr=process_stderr)

    @staticmethod
    async def read_stream(stream: StreamReader, collector: list[str], log_level) -> None:        # type: ignore[no-untyped-def]
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode().rstrip()
            collector.append(decoded)
            logging.log(log_level, decoded)
            for handler in logging.getLogger().handlers:
                handler.flush()


class PytestResolver(ABCTargetResolver[TestTargetType]):
    """Create :class:`PytestRunnable` from :class:`TestTargetType` by resolving path to tests"""
    def _resolve_target(self, target: TestTargetType) -> PytestRunnable:
        return PytestRunnable(test_path=self._get_path(target))

    @staticmethod
    def _get_path(target: TestTargetType) -> str:
        """Get full path to run tests in pytest"""
        path = inspect.getfile(target)
        if path.endswith("__init__.py"):
            path = target.__path__[0]  # type: ignore[union-attr]

        path = str(Path(path))

        if not isinstance(target, ModuleType):
            pytest_test_name = target.__qualname__.replace('.', '::')
            path += f'::{pytest_test_name}'

        return path


class ABCPytestDirective(ABCDirective[TestTargetType]):
    """
    Base class of Pytest directives.

    Use :class:`PytestResolver` as target_resolver.
    """
    def __init__(
        self,
        *raw_items: ABCRunnable | TestTargetType,
        run_strategy: ABCRunStrategy,
        run_args: tuple[str, ...] = tuple(),
    ):
        super().__init__(
            *raw_items,
            run_strategy=run_strategy,
            run_args=run_args,
            target_resolver=PytestResolver()
        )


class PytestSequenceDirective(ABCPytestDirective):
    """
    Pytest Directive

    * Runs sequentially
    * Ignores errors
    * Result is_ok if at least one item passes
    """

    def __init__(
        self,
        *raw_items: ABCRunnable | TestTargetType,
        run_args: tuple[str, ...] = tuple(),
    ):
        super().__init__(
            *raw_items,
            run_args=run_args,
            run_strategy=SequenceRunStrategy(),
        )


class PytestChainDirective(ABCPytestDirective):
    """
    Pytest Directive

    * Runs sequentially
    * Stop on first error
    * Result is_ok if all items passed
    """

    def __init__(
        self,
        *raw_items: ABCRunnable | TestTargetType,
        run_args: tuple[str, ...] = tuple(),
    ):
        super().__init__(
            *raw_items,
            run_args=run_args,
            run_strategy=ChainRunStrategy(),
        )


class PytestParallelDirective(ABCPytestDirective):
    """
    Pytest Directive

    * Runs parallel
    * Ignores errors
    * Result is_ok if all items passes
    """

    def __init__(
        self,
        *raw_items: ABCRunnable | TestTargetType,
        run_args: tuple[str, ...] = tuple(),
    ):
        super().__init__(
            *raw_items,
            run_args=run_args,
            run_strategy=ParallelRunStrategy(),
        )


# shortcuts
sequence = PytestSequenceDirective
chain = PytestChainDirective
parallel = PytestParallelDirective
