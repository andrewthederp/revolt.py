from __future__ import annotations

from inspect import Parameter
from typing import TYPE_CHECKING, Any, Iterable
from .parameter import RevoltParameter

from typing_extensions import TypeVar

if TYPE_CHECKING:
    from .client import CommandsClient
    from .context import Context


__all__ = ("evaluate_parameters", "ClientT_Co", "ClientT_D", "ClientT_Co_D", "ContextT")

ClientT_Co = TypeVar("ClientT_Co", bound="CommandsClient", covariant=True)
ClientT_D = TypeVar("ClientT_D", bound="CommandsClient", default="CommandsClient")
ClientT_Co_D = TypeVar("ClientT_Co_D", bound="CommandsClient", default="CommandsClient", covariant=True)
ContextT = TypeVar("ContextT", bound="Context", default="Context")


def evaluate_parameters(parameters: Iterable[Parameter], globals: dict[str, Any]) -> list[Parameter]:
    new_parameters: list[Parameter] = []

    for parameter in parameters:
        if isinstance(parameter.default, RevoltParameter):
            parameter = parameter.default
        else:
            annotation = parameter.annotation
            if parameter.annotation is not parameter.empty:
                if isinstance(parameter.annotation, str):
                    annotation = eval(annotation, globals)

            parameter = RevoltParameter(
                name=parameter.name,
                kind=parameter.kind,
                annotation=annotation,
            )

        new_parameters.append(parameter)

    return new_parameters
