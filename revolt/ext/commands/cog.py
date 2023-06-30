from __future__ import annotations

from typing import Any, Generic, Optional, cast
from typing_extensions import Self

from .command import Command
from .utils import ClientT_D

__all__ = ("Cog", "CogMeta")

class CogMeta(type, Generic[ClientT_D]):
    _commands: list[Command[ClientT_D]]
    qualified_name: str

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any], *, qualified_name: Optional[str] = None, extras: dict[str, Any] | None = None) -> Self:
        commands: list[Command[ClientT_D]] = []
        self = super().__new__(cls, name, bases, attrs)
        extras = extras or {}

        for base in reversed(self.__mro__):
            for value in base.__dict__.values():
                if isinstance(value, Command):
                    for key, value in extras.items():
                        setattr(value, key, value)

                    commands.append(cast(Command[ClientT_D], value))  # cant verify generic at runtime so must cast


        self._commands = commands
        self.qualified_name = qualified_name or name
        return self

class Cog(Generic[ClientT_D], metaclass=CogMeta):
    _commands: list[Command[ClientT_D]]
    qualified_name: str

    def cog_load(self) -> None:
        """A special method that is called when the cog gets loaded."""
        pass

    def cog_unload(self) -> None:
        """A special method that is called when the cog gets removed."""
        pass

    def _inject(self, client: ClientT_D) -> None:
        client.cogs[self.qualified_name] = self

        for command in self._commands:
            command.cog = self

            if command.parent is None:
                client.add_command(command)

        self.cog_load()

    def _uninject(self, client: ClientT_D) -> None:
        for name, command in client.all_commands.copy().items():
            if command in self._commands:
                del client.all_commands[name]

        self.cog_unload()

    @property
    def commands(self) -> list[Command[ClientT_D]]:
        return self._commands
