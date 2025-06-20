from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, TypeVar, Callable, Coroutine, Any

Target = TypeVar("Target")


class ABCTargetResolver(ABC):
    def to_runnable(self, target: ABCRunnable | Target) -> ABCRunnable:
        if isinstance(target, ABCRunnable):
            return target
        return self._resolve_target(target=target)

    @abstractmethod
    def _resolve_target(self, target: Target) -> ABCRunnable: ...


@dataclass
class RunResult:
    is_ok: bool


class ABCRunnable:
    @abstractmethod
    async def run(self,  *run_args: str) -> RunResult: ...


class ABCRunStrategy:
    @abstractmethod
    async def run(
        self,
        items: list[ABCRunnable],
        run_item_callback: Callable[[ABCRunnable], Coroutine[Any, Any, RunResult]]
    ) -> None: ...

    @abstractmethod
    def is_run_ok(self, items_run_results: Iterable[RunResult]) -> bool: ...


class ABCDirective(ABCRunnable):
    _items: list[ABCRunnable]
    _run_results: list[RunResult]

    def __init__(
        self,
        *raw_items: ABCRunnable | Target,
        run_strategy: ABCRunStrategy,
        target_resolver: ABCTargetResolver,
        run_args: tuple[str, ...] = tuple(),
    ):
        self._run_args = run_args

        self._run_strategy = run_strategy
        self._target_resolver = target_resolver

        self._items = list(
            map(lambda item: self._target_resolver.to_runnable(item), raw_items)
        )

    async def run(self, *run_args: str) -> RunResult:
        self._run_args += run_args
        await self._run_strategy.run(items=self._items, run_item_callback=self._run_item)
        return RunResult(is_ok=self._run_strategy.is_run_ok(self._run_results))

    async def _run_item(self, item: ABCRunnable) -> RunResult:
        item_result = await item.run(*self._run_args)
        self._run_results.append(item_result)
        return item_result

