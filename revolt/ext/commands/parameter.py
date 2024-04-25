import inspect
from typing import Any, TYPE_CHECKING, TypeVar

from revolt.utils import maybe_coroutine

if TYPE_CHECKING:
    pass

ClientT = TypeVar("ClientT", bound="CommandsClient")

empty = inspect.Parameter.empty


class RevoltParameter(inspect.Parameter):
    def __init__(
            self,
            name: str,
            kind: Any,
            *,
            default: Any = empty,
            annotation: Any = empty,
            description: str = None,
            displayed_default: str = empty,
            displayed_name: str = empty
    ):
        super().__init__(name, kind, default=default, annotation=annotation)
        self._description = description
        self._displayed_default = displayed_default
        self._displayed_name = displayed_name

    @property
    def required(self):
        return self.default is empty

    @property
    def description(self):
        return self._description

    @property
    def display_default(self):
        return self._displayed_default if self._displayed_default is not empty else None

    @property
    def display_name(self):
        return self.name if self._display_name is empty else self._displayed_name

    async def get_default(self, ctx):
        if callable(self.default):
            return await maybe_coroutine(self.default, ctx)
        return self.default


def parameter(
        *,
        displayed_name: str,
        default: Any = empty,
        converter: Any = empty,
        description: str = None,
        displayed_default: str = empty,
        kind: Any = inspect.Parameter.POSITIONAL_OR_KEYWORD
):
    return RevoltParameter(
        displayed_name,
        kind,
        default=default,
        annotation=converter,
        description=description,
        displayed_default=displayed_default,
        displayed_name=displayed_name
    )

param = parameter
