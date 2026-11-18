from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


DatabaseRow = dict[str, Any]
QueryParameters = Sequence[Any]


class DatabaseExecutor(Protocol):
    async def execute(
        self,
        *,
        query: str,
        parametros: QueryParameters = (),
        fetch: bool = False,
        timeout: int = 300,
        autocommit: bool = False,
    ) -> list[DatabaseRow] | int:
        ...
