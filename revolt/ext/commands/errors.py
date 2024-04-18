from revolt import RevoltError

__all__ = (
    "CommandError",
    "CommandNotFound",
    "NoClosingQuote",
    "CheckError",
    "NotBotOwner",
    "NotServerOwner",
    "ServerOnly",
    "MissingPermissionsError",
    "MissingRequiredArgument",
    "ConverterError",
    "InvalidLiteralArgument",
    "BadBoolArgument",
    "CategoryConverterError",
    "ChannelConverterError",
    "TextChannelConverterError",
    "UserConverterError",
    "MemberConverterError",
    "UnionConverterError",
    "MissingSetup",
    "CommandOnCooldown",
)


class CommandError(RevoltError):
    """base error for all command's related errors"""


class CommandNotFound(CommandError):
    """Raised when a command isn't found.

    Parameters
    -----------
    command_name: :class:`str`
        The name of the command that wasn't found
    """
    __slots__ = ("command_name",)

    def __init__(self, command_name: str):
        self.command_name: str = command_name


class NoClosingQuote(CommandError):
    """Raised when there is no closing quote for a command argument"""


class CheckError(CommandError):
    """Raised when a check fails for a command"""


class NotBotOwner(CheckError):
    """Raised when the `is_bot_owner` check fails"""


class NotServerOwner(CheckError):
    """Raised when the `is_server_owner` check fails"""


class ServerOnly(CheckError):
    """Raised when a check requires the command to be ran in a server"""


class MissingPermissionsError(CheckError):
    """Raised when a check requires permissions the user does not have

    Attributes
    -----------
    permissions: :class:`dict[str, bool]`
        The permissions which the user did not have
    """

    def __init__(self, permissions: dict[str, bool]):
        self.permissions = permissions


class MissingRequiredArgument(CommandError):
    """
    Raised when a required argument is missing

    Attributes
    -----------
    missing: :class:`str`
        The name of the missing argument
    """
    def __init__(self, missing: str):
        self.missing = missing


class ConverterError(CommandError):
    """
    Base class for all converter errors

    Attributes
    -----------
    argument: :class:`str`
        The argument that made the converter fail
    """
    def __init__(self, argument):
        self.argument = argument


class InvalidLiteralArgument(ConverterError):
    """
    Raised when the argument is not a valid literal argument

    Attributes
    -----------
    valid_literals: :class:`tuple[str]`
        A tuple of the literals `argument` could be in
    """
    def __init__(self, argument, valid_literals):
        super().__init__(argument)
        self.valid_literals = valid_literals


class BadBoolArgument(ConverterError):
    """Raised when the bool converter fails"""


class CategoryConverterError(ConverterError):
    """Raised when the Category converter fails"""


class ChannelConverterError(ConverterError):
    """Raised when the Channel converter fails"""


class TextChannelConverterError(ChannelConverterError):
    """Raised when the Channel converter fails"""


class UserConverterError(ConverterError):
    """Raised when the User converter fails"""


class MemberConverterError(ConverterError):
    """Raised when the Member converter fails"""


class UnionConverterError(ConverterError):
    """Raised when all converters in a union fail"""


class MissingSetup(CommandError):
    """Raised when an extension is missing the `setup` function"""


class CommandOnCooldown(CommandError):
    """Raised when a command is on cooldown

    Attributes
    -----------
    retry_after: :class:`float`
        How long the user must wait until the cooldown resets
    """

    __slots__ = ("retry_after",)

    def __init__(self, retry_after: float):
        self.retry_after: float = retry_after
