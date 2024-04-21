from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, TypeVar

import revolt
from revolt import Category, Channel, Member, User, utils, TextChannel, VoiceChannel, ChannelType

from .context import Context
from .errors import (BadBoolArgument, CategoryConverterError,
                     ChannelConverterError, MemberConverterError, ServerOnly,
                     UserConverterError, TextChannelConverterError)

if TYPE_CHECKING:
    from .client import CommandsClient

__all__: tuple[str, ...] = ("bool_converter", "category_converter", "channel_converter", "user_converter", "member_converter", "IntConverter", "BoolConverter", "CategoryConverter", "UserConverter", "MemberConverter", "ChannelConverter", "TextChannelConverter")

channel_regex: re.Pattern[str] = re.compile("<?#?([A-z0-9]{26})>?")
user_regex: re.Pattern[str] = re.compile("<?@?([A-z0-9]{26})>?")

ClientT = TypeVar("ClientT", bound="CommandsClient")


def bool_converter(arg: str, _: Context[ClientT]) -> bool:
    lowered = arg.lower()
    if lowered in ("yes", "true", "ye", "y", "1", "on", "enable"):
        return True
    elif lowered in ("no", "false", "n", "f", "0", "off", "disabled"):
        return False
    else:
        raise BadBoolArgument(lowered)


def category_converter(arg: str, context: Context[ClientT]) -> Category:
    if not context.server_id:
        raise ServerOnly

    category = context.server.get_category(arg)

    if not category:
        category = utils.get(context.server.categories, name=arg)

    if category:
        return category

    raise CategoryConverterError(arg)


def channel_converter(arg: str, context: Context[ClientT]) -> Channel:
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


def text_channel_converter(arg: str, context: Context[ClientT]) -> Channel:
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


def user_converter(arg: str, context: Context[ClientT]) -> User:
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


def member_converter(arg: str, context: Context[ClientT]) -> Member:
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


def int_converter(arg: str, _: Context[ClientT]) -> int:
    return int(arg)


IntConverter = Annotated[int, int_converter]
BoolConverter = Annotated[bool, bool_converter]
CategoryConverter = Annotated[Category, category_converter]
UserConverter = Annotated[User, user_converter]
MemberConverter = Annotated[Member, member_converter]
ChannelConverter = Annotated[Channel, channel_converter]
TextChannelConverter = Annotated[TextChannel, text_channel_converter]
