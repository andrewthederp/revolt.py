from __future__ import annotations

import inspect
import re
from typing import (Annotated, Any, Literal, TYPE_CHECKING, TypeVar, Union, get_args, get_origin)

import revolt
from revolt import Category, Channel, ChannelType, Member, Role, TextChannel, User, utils
from revolt.utils import maybe_coroutine
from .errors import (BadBoolArgument, CategoryConverterError, ChannelConverterError, MemberConverterError,
                     RoleConverterError, ServerOnly, TextChannelConverterError, UserConverterError, ConverterError)
from .utils import ClientT_Co_D

if TYPE_CHECKING:
    from .context import Context

__all__: tuple[str, ...] = (
    "bool_converter",
    "category_converter",
    "channel_converter",
    "text_channel_converter",
    "user_converter",
    "member_converter",
    "role_converter",
    "int_converter",
    "IntConverter",
    "BoolConverter",
    "CategoryConverter",
    "UserConverter",
    "MemberConverter",
    "ChannelConverter",
    "TextChannelConverter",
    "RoleConverter",
    "handle_origin",
    "convert_argument"
)

channel_regex: re.Pattern[str] = re.compile("<?#?([A-z0-9]{26})>?")
user_regex: re.Pattern[str] = re.compile("<?@?([A-z0-9]{26})>?")

ClientT = TypeVar("ClientT", bound="CommandsClient")


def bool_converter(_: Context[ClientT], arg: str) -> bool:
    lowered = arg.lower()
    if lowered in ("yes", "true", "ye", "y", "1", "on", "enable"):
        return True
    elif lowered in ("no", "false", "n", "f", "0", "off", "disabled"):
        return False
    else:
        raise BadBoolArgument(lowered)


def category_converter(context: Context[ClientT], arg: str) -> Category:
    if not context.server_id:
        raise ServerOnly

    category = context.server.get_category(arg)

    if not category:
        category = utils.get(context.server.categories, name=arg)

    if category:
        return category

    raise CategoryConverterError(arg)


def channel_converter(context: Context[ClientT], arg: str) -> Channel:
    if not context.server_id:
        raise ServerOnly

    if match := channel_regex.match(arg):
        channel_id = match.group(1)

        channel = context.server.get_channel(channel_id)
        if channel:
            return channel

    channel = utils.get(context.server.channels, name=arg)
    if channel:
        return channel

    raise ChannelConverterError(arg)


def text_channel_converter(context: Context[ClientT], arg: str) -> Channel:
    if not context.server_id:
        raise ServerOnly

    if match := channel_regex.match(arg):
        channel_id = match.group(1)

        channel = context.server.get_channel(channel_id)
        if channel and isinstance(channel, TextChannel):
            return channel
    else:
        channel = utils.get(context.server.channels, name=arg, channel_type=ChannelType.text_channel)
        if channel:
            return channel

    raise TextChannelConverterError(arg)


def user_converter(context: Context[ClientT], arg: str) -> User:
    if match := user_regex.match(arg):
        arg = match.group(1)

        if member := context.client.get_user(arg):
            return member

    else:
        parts = arg.split("#")

        if len(parts) == 1:
            user = (
                utils.get(context.client.users, original_name=arg)
                or utils.get(context.client.users, display_name=arg)
            )

            if user:
                return user
        elif len(parts) == 2:
            user = (
                utils.get(context.client.users, original_name=parts[0], discriminator=parts[1])
                or utils.get(context.client.users, display_name=parts[0], discriminator=parts[1])
            )

            if user:
                return user

    raise UserConverterError(arg)


def member_converter(context: Context[ClientT], arg: str) -> Member:
    if not context.server_id:
        raise ServerOnly

    if match := user_regex.match(arg):
        arg = match.group(1)

        if member := context.server.get_member(arg):
            return member

    else:
        parts = arg.split("#")

        if len(parts) == 1:
            member = utils.get(context.server.members, original_name=arg) or utils.get(context.server.members, display_name=arg)
            if member:
                return member
        elif len(parts) == 2:
            member = (utils.get(context.server.members, original_name=parts[0], discriminator=parts[1]) or
                      utils.get(context.server.members, display_name=parts[0], discriminator=parts[1]))
            if member:
                return member

    raise MemberConverterError(arg)


def role_converter(context: Context[ClientT], arg: str) -> Role:
    role = context.server.get_role(arg)

    if not role:
        role = revolt.utils.get(context.server.roles, name=arg)

    if not role:
        raise RoleConverterError(f"Could not find role {arg}")

    return role


def int_converter(_: Context[ClientT], arg: str) -> int:
    return int(arg)


# These will remain for legacy support!
IntConverter = Annotated[int, int_converter]
BoolConverter = Annotated[bool, bool_converter]
UserConverter = Annotated[User, user_converter]
MemberConverter = Annotated[Member, member_converter]
RoleConverter = Annotated[Role, role_converter]
ChannelConverter = Annotated[Channel, channel_converter]
CategoryConverter = Annotated[Category, category_converter]
TextChannelConverter = Annotated[TextChannel, text_channel_converter]

_converting_lookup = {
    int: int_converter,
    bool: bool_converter,
    User: user_converter,
    Member: member_converter,
    Role: role_converter,
    Channel: channel_converter,
    TextChannel: text_channel_converter,
    Category: category_converter
}


async def handle_origin(
        context: Context[ClientT_Co_D], origin: Any, annotation: Any, parameter_name: str, arg: str
        ) -> Any:
    if origin is Union:
        possible_converters = get_args(annotation)
        for converter in possible_converters:
            if converter is not type(None):
                try:
                    return await convert_argument(context, arg, converter, parameter_name)
                except Exception:
                    pass

        if type(None) in possible_converters:  # typing.Optional
            context.view.undo()
            return None

        raise UnionConverterError(arg)

    elif origin is Annotated:
        annotated_args = get_args(annotation)

        if origin := get_origin(annotated_args[0]):
            return await handle_origin(context, origin, annotated_args[1], parameter_name, arg)
        else:
            return await convert_argument(context, arg, annotated_args[1], parameter_name)

    elif origin is Literal:
        args = get_args(annotation)
        if arg in args:
            return arg
        else:
            error = InvalidLiteralArgument(arg, args)
            error.parameter_name = parameter_name
            raise error


async def convert_argument(context: Context[ClientT_Co_D], arg: str, annotation: Any, parameter_name: str) -> Any:
    if annotation is not inspect.Signature.empty:
        if annotation is str:  # no converting is needed - it's already a string
            return arg

        annotation = _converting_lookup.get(annotation, annotation)
        origin: Any
        if origin := get_origin(annotation):
            return await handle_origin(context, origin, annotation, parameter_name, arg)
        else:
            try:
                if "convert" in dir(annotation):
                    return await maybe_coroutine(annotation.convert, context, arg)
                else:
                    return await maybe_coroutine(annotation, context, arg)
            except ConverterError as exc:
                exc.parameter_name = parameter_name
                raise exc
    else:
        return arg
