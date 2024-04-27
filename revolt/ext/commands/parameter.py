import inspect
from typing import Any, TYPE_CHECKING, TypeVar

from revolt.utils import maybe_coroutine, Missing

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

    def replace(
        self,
        *,
        name: str = Missing,
        kind: Any = Missing,
        default: Any = Missing,
        annotation: Any = Missing,
        description: str = Missing,
        displayed_default: Any = Missing,
        displayed_name: Any = Missing,
    ):
        if name is Missing:
            name = self._name
        if kind is Missing:
            kind = self._kind
        if default is Missing:
            default = self._default
        if annotation is Missing:
            annotation = self._annotation
        if description is Missing:
            description = self._description
        if displayed_default is Missing:
            displayed_default = self._displayed_default
        if displayed_name is Missing:
            displayed_name = self._displayed_name

        return RevoltParameter(
            name=name,
            kind=kind,
            default=default,
            annotation=annotation,
            description=description,
            displayed_default=displayed_default,
            displayed_name=displayed_name,
        )


def parameter(
        *,
        displayed_name: str = empty,
        default: Any = empty,
        converter: Any = empty,
        description: str = None,
        displayed_default: str = empty,
        kind: Any = inspect.Parameter.POSITIONAL_OR_KEYWORD
):
    return RevoltParameter(
        "_override",
        kind,
        default=default,
        annotation=converter,
        description=description,
        displayed_default=displayed_default,
        displayed_name=displayed_name
    )

param = parameter
