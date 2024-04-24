from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Optional

import revolt
from revolt.utils import maybe_coroutine

from .command import Command
from .group import Group
from .utils import ClientT_Co_D
from .errors import CheckError

if TYPE_CHECKING:
    from .view import StringView
    from revolt.state import State

__all__ = (
    "Context",
)


class Context(revolt.Messageable, Generic[ClientT_Co_D]):
    """Stores metadata the commands execution.

    Attributes
    -----------
    command: Optional[:class:`Command`]
        The command, this can be `None` when no command was found and the error handler is being executed
    invoked_with: :class:`str`
        The command name that was used, this can be an alias, the commands name or a command that doesn't exist
    prefix: :class:`str`
        The prefix that triggered the command
    message: :class:`Message`
        The message that was sent to invoke the command
    channel: :class:`Messageable`
        The channel the command was invoked in
    server_id: Optional[:class:`Server`]
        The server the command was invoked in
    author: Union[:class:`Member`, :class:`User`]
        The user or member that invoked the commad, will be :class:`User` in DMs
    args: list[:class:`str`]
        The positional arguments being passed to the command
    kwargs: dict[:class:`str`, Any]
        The keyword arguments being passed to the command
    client: :class:`CommandsClient`
        The revolt client
    """
    __slots__ = ("command", "invoked_with", "prefix", "args", "message", "channel", "author", "view", "kwargs", "state", "client", "server_id")

    async def _get_channel_id(self) -> str:
        return self.channel.id

    def __init__(self, command: Optional[Command[ClientT_Co_D]], invoked_with: str, prefix: str, view: StringView, message: revolt.Message, client: ClientT_Co_D):
        self.command: Command[ClientT_Co_D] | None = command
        self.invoked_with: str = invoked_with
        self.prefix: str = prefix
        self.view: StringView = view
        self.message: revolt.Message = message
        self.client: ClientT_Co_D = client
        self.args: list[Any] = []
        self.kwargs: dict[str, Any] = {}
        self.server_id: str | None = message.server_id
        self.channel: revolt.TextChannel | revolt.GroupDMChannel | revolt.DMChannel | revolt.SavedMessageChannel = message.channel
        self.author: revolt.Member | revolt.User = message.author
        self.state: State = message.state

    @property
    def server(self) -> revolt.Server:
        """:class:`Server` The server this context belongs to"""
        if not self.server_id:
            return None

        return self.state.get_server(self.server_id)

    async def invoke(self) -> Any:
        """Invokes the command.

        .. note:: If the command is `None`, this function will do nothing.

        Parameters
        -----------
        args: list[:class:`str`]
            The args being passed to the command
        """

        if command := self.command:
            if isinstance(command, Group):
                try:
                    subcommand_name = self.view.get_next_word()
                except StopIteration:
                    pass
                else:
                    if subcommand := command.get_command(subcommand_name):
                        self.command = subcommand
                        return await self.invoke()

                    self.view.undo()

            if not await self.client.global_check(self):
                raise CheckError(f"the global check for the command failed")

            if not await self.can_run():
                raise CheckError(f"the check(s) for the command failed")

            await command.run_cooldown(self)
            await command.parse_arguments(self)
            return await command.invoke(self, *self.args, **self.kwargs)

    async def can_run(self, command: Optional[Command[ClientT_Co_D]] = None) -> bool:
        """Runs all the command checks, and returns true if all of them pass"""
        command = command or self.command
        return all([await maybe_coroutine(check, self) for check in (command.checks if command else [])])

    async def send_help(self, argument: Command[Any] | Group[Any] | ClientT_Co_D | None = None) -> None:
        argument = argument or self.client

        command = self.client.get_command("help")
        await command.invoke(self, argument)
