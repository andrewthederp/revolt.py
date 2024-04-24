from __future__ import annotations

import inspect
import traceback
from contextlib import suppress
from typing import (TYPE_CHECKING, Annotated, Any, Callable, Coroutine,
                    Generic, Literal, Optional, Union, get_args, get_origin)
from typing_extensions import ParamSpec

from revolt.utils import maybe_coroutine

from .errors import CommandOnCooldown, InvalidLiteralArgument, UnionConverterError, MissingRequiredArgument, ConverterError
from .utils import ClientT_Co_D, evaluate_parameters, ClientT_Co
from .cooldown import BucketType, CooldownMapping

if TYPE_CHECKING:
    from .checks import Check
    from .cog import Cog
    from .context import Context
    from .group import Group

__all__: tuple[str, ...] = (
    "Command",
    "command"
)

NoneType: type[None] = type(None)
P = ParamSpec("P")


class Command(Generic[ClientT_Co_D]):
    """Class for holding info about a command.

    Parameters
    -----------
    callback: Callable[..., Coroutine[Any, Any, Any]]
        The callback for the command
    name: :class:`str`
        The name of the command
    aliases: list[:class:`str`]
        The aliases of the command
    parent: Optional[:class:`Group`]
        The parent of the command if this command is a subcommand
    cog: Optional[:class:`Cog`]
        The cog the command is apart of.
    usage: Optional[:class:`str`]
        The usage string for the command
    checks: Optional[list[Callable]]
        The list of checks the command has
    cooldown: Optional[:class:`Cooldown`]
        The cooldown for the command to restrict how often the command can be used
    description: Optional[:class:`str`]
        The commands description if it has one
    hidden: :class:`bool`
        Whether the command should be hidden from the help command
    """
    __slots__ = ("callback", "name", "aliases", "signature", "checks", "parent", "_error_handler", "cog", "description", "usage", "parameters", "hidden", "cooldown", "cooldown_bucket")

    def __init__(
            self,
            callback: Callable[..., Coroutine[Any, Any, Any]],
            name: str,
            *,
            aliases: list[str] | None = None,
            usage: Optional[str] = None,
            checks: list[Check[ClientT_Co_D]] | None = None,
            cooldown: Optional[CooldownMapping] | None = None,
            bucket: Optional[BucketType | Callable[[Context[ClientT_Co_D]], Coroutine[Any, Any, str]]] = None,
            description: str | None = None,
            hidden: bool = False,
    ):
        self.callback: Callable[..., Coroutine[Any, Any, Any]] = callback
        self.name: str = name
        self.aliases: list[str] = aliases or []
        self.usage: str | None = usage
        self.signature: inspect.Signature = inspect.signature(self.callback)
        self.parameters: list[inspect.Parameter] = evaluate_parameters(self.signature.parameters.values(), getattr(callback, "__globals__", {}))
        self.checks: list[Check[ClientT_Co_D]] = checks or getattr(callback, "_checks", [])
        self.cooldown: CooldownMapping | None = cooldown or getattr(callback, "_cooldown", None)
        self.cooldown_bucket: BucketType | Callable[[Context[ClientT_Co_D]], Coroutine[Any, Any, str]] = bucket or getattr(callback, "_bucket", BucketType.default)
        self.parent: Optional[Group[ClientT_Co_D]] = None
        self.cog: Optional[Cog[ClientT_Co_D]] = None
        self._error_handler: Callable[[Any, Context[ClientT_Co_D], Exception], Coroutine[Any, Any, Any]] = type(self)._default_error_handler
        self.description: str | None = description or callback.__doc__
        if self.description:
            self.description = self.description.strip()
        self.hidden: bool = hidden

    async def invoke(self, context: Context[ClientT_Co_D], *args: Any, **kwargs: Any) -> Any:
        """Runs the command and calls the error handler if the command errors.

        Parameters
        -----------
        context: :class:`Context`
            The context for the command
        args: list[:class:`str`]
            The arguments for the command
        """
        try:
            return await self.callback(self.cog or context.client, context, *args, **kwargs)
        except Exception as err:
            return await self._error_handler(self.cog or context.client, context, err)

    def __call__(self, context: Context[ClientT_Co_D], *args: Any, **kwargs: Any) -> Any:
        return self.invoke(context, *args, **kwargs)

    def error(self, func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        """Sets the error handler for the command.

        Parameters
        -----------
        func: Callable[..., Coroutine[Any, Any, Any]]
            The function for the error handler

        Example
        --------
        .. code-block:: python3

            @mycommand.error
            async def mycommand_error(self, ctx, error):
                await ctx.send(str(error))

        """
        self._error_handler = func
        return func

    async def _default_error_handler(self, ctx: Context[ClientT_Co_D], error: Exception):
        ctx.client.dispatch("command_error", ctx, error)

    @classmethod
    async def handle_origin(cls, context: Context[ClientT_Co_D], origin: Any, annotation: Any, parameter_name: str, arg: str) -> Any:
        if origin is Union:
            possible_converters = get_args(annotation)
            for converter in possible_converters:
                if converter is not type(None):
                    try:
                        return await cls.convert_argument(arg, converter, parameter_name, context)
                    except Exception:
                        pass

            if type(None) in possible_converters:
                context.view.undo()
                return None

            raise UnionConverterError(arg)

        elif origin is Annotated:
            annotated_args = get_args(annotation)

            if origin := get_origin(annotated_args[0]):
                return await cls.handle_origin(context, origin, annotated_args[1], parameter_name, arg)
            else:
                return await cls.convert_argument(arg, annotated_args[1], parameter_name, context)

        elif origin is Literal:
            args = get_args(annotation)
            if arg in args:
                return arg
            else:
                error = InvalidLiteralArgument(arg, args)
                error.parameter_name = parameter_name
                raise error

    @classmethod
    async def convert_argument(cls, arg: str, annotation: Any, parameter_name: str, context: Context[ClientT_Co_D]) -> Any:
        if annotation is not inspect.Signature.empty:
            if annotation is str:  # no converting is needed - it's already a string
                return arg

            origin: Any
            if origin := get_origin(annotation):
                return await cls.handle_origin(context, origin, annotation, parameter_name, arg)
            else:
                try:
                    return await maybe_coroutine(annotation, arg, context)
                except ConverterError as exc:
                    exc.parameter_name = parameter_name
                    raise exc
        else:
            return arg

    async def parse_arguments(self, context: Context[ClientT_Co_D]) -> None:
        # please pr if you can think of a better way to do this

        for parameter in self.parameters[2:]:
            if parameter.kind == parameter.KEYWORD_ONLY:
                string = context.view.get_rest()

                if string == "":
                    if parameter.default is not parameter.empty:
                        context.kwargs[parameter.name] = parameter.default
                    else:
                        raise MissingRequiredArgument(parameter.name)
                else:
                    arg = await self.convert_argument(string, parameter.annotation, parameter.name, context)
                    context.kwargs[parameter.name] = arg

            elif parameter.kind == parameter.VAR_POSITIONAL:
                with suppress(StopIteration):
                    while True:
                        context.args.append(await self.convert_argument(context.view.get_next_word(), parameter.annotation, parameter.name, context))

            elif parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.POSITIONAL_ONLY):
                try:
                    rest = context.view.get_next_word()
                    arg = await self.convert_argument(rest, parameter.annotation, parameter.name, context)
                except StopIteration:
                    if parameter.default is not parameter.empty:
                        arg = parameter.default
                        context.view.undo()
                    else:
                        raise MissingRequiredArgument(parameter.name)

                context.args.append(arg)

    async def run_cooldown(self, context: Context[ClientT_Co_D]) -> None:
        if mapping := self.cooldown:
            if isinstance(self.cooldown_bucket, BucketType):
                key = self.cooldown_bucket.resolve(context)
            else:
                key = await self.cooldown_bucket(context)

            cooldown = mapping.get_bucket(key)

            if retry_after := cooldown.update_cooldown():
                raise CommandOnCooldown(retry_after)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name=\"{self.name}\">"

    @property
    def short_description(self) -> Optional[str]:
        """Returns the first line of the description or None if there is no description."""
        if self.description:
            return self.description.split("\n")[0]

    def get_usage(self) -> str:
        """Returns the usage string for the command."""
        if self.usage:
            return self.usage

        parents: list[str] = []

        if self.parent:
            parent = self.parent

            while parent:
                parents.append(parent.name)
                parent = parent.parent

        parameters: list[str] = []

        for parameter in self.parameters[2:]:
            if parameter.kind == parameter.POSITIONAL_OR_KEYWORD:
                if parameter.default is not parameter.empty:
                    parameters.append(f"[{parameter.name}]")
                else:
                    parameters.append(f"<{parameter.name}>")
            elif parameter.kind == parameter.KEYWORD_ONLY:
                if parameter.default is not parameter.empty:
                    parameters.append(f"[{parameter.name}]")
                else:
                    parameters.append(f"<{parameter.name}...>")
            elif parameter.kind == parameter.VAR_POSITIONAL:
                parameters.append(f"[{parameter.name}...]")

        return f"{' '.join(parents[::-1])} {self.name} {' '.join(parameters)}"


def command(
    *,
    name: Optional[str] = None,
    aliases: Optional[list[str]] = None,
    cls: type[Command[ClientT_Co]] = Command,
    usage: Optional[str] = None,
    hidden: bool = False,
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Command[ClientT_Co]]:
    """A decorator that turns a function into a :class:`Command`.n

    Parameters
    -----------
    name: Optional[:class:`str`]
        The name of the command, this defaults to the functions name
    aliases: Optional[list[:class:`str`]]
        The aliases of the command, defaults to no aliases
    cls: type[:class:`Command`]
        The class used for creating the command, this defaults to :class:`Command` but can be used to use a custom command subclass
    usage: Optional[:class:`str`]
        The signature for how the command should be called
    hidden: :class:`bool`
        A boolean that indicates if the command should be hidden from help

    Returns
    --------
    Callable[Callable[..., Coroutine], :class:`Command`]
        A function that takes the command callback and returns a :class:`Command`
    """
    def inner(func: Callable[..., Coroutine[Any, Any, Any]]) -> Command[ClientT_Co]:
        return cls(func, name or func.__name__, aliases=aliases or [], usage=usage, hidden=hidden)

    return inner
