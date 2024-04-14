import revolt
from revolt.ext import commands
from jishaku.repl.walkers import KeywordTransformer
import import_expression
from traceback import format_exception
import io
import ast

CORO_FUNC = f"""
async def func():
    from importlib import import_module as {import_expression.constants.IMPORTER}

    try:
        pass
    finally:
        pass
"""


def embed_creator(text, num, *, title='', prefix='', suffix='', color=None, colour=None):
    if color is not None and colour is not None:
        raise ValueError

    return [revolt.SendableEmbed(title=title, description=prefix + (text[i:i + num]) + suffix, colour=color or colour) for i in range(0, len(text), num)]


def clean_code(content):
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content


def convert_code(code):
    user_code = import_expression.parse(code, mode='exec')
    mod = import_expression.parse(CORO_FUNC, mode='exec')

    for node in ast.walk(mod):
        node.lineno = -100_000
        node.end_lineno = -100_000

    definition = mod.body[-1]
    assert isinstance(definition, ast.AsyncFunctionDef)

    try_block = definition.body[-1]
    assert isinstance(try_block, ast.Try)

    try_block.body.extend(user_code.body)
    ast.fix_missing_locations(mod)

    KeywordTransformer().generic_visit(try_block)

    last_expr = try_block.body[-1]

    if not isinstance(last_expr, ast.Expr):
        return mod

    if not isinstance(last_expr.value, ast.Yield):
        yield_stmt = ast.Yield(last_expr.value)
        ast.copy_location(yield_stmt, last_expr)

        yield_expr = ast.Expr(yield_stmt)
        ast.copy_location(yield_expr, last_expr)

        try_block.body[-1] = yield_expr

    return mod


def jump_url(message):
    return f"https://app.revolt.chat/server/{message.server.id}/channel/{message.channel.id}/{message.id}"


class Owner(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.last_result = None

    async def handle_send(self, ctx, result):
        if isinstance(result, revolt.Message):
            return await ctx.send(f"<Message <{jump_url(result)}>>")

        if isinstance(result, revolt.File):
            return await ctx.send(attachments=[result])

        if isinstance(result, revolt.SendableEmbed):
            return await ctx.send(embed=result)

        # if isinstance(result, discord.ui.View):
        #     return await ctx.send(view=result)

        if isinstance(result, type(None)):
            return

        if not isinstance(result, str):
            result = repr(result)

        if len(result) <= 2000:
            if result.strip() == '':
                result = "\u200b"

            result = result.replace(self.client.http.token, "[token omitted]")

            return await ctx.send(result)

        embeds = embed_creator(
            result, 3950, title="Code eval success", prefix='```py\n', suffix='```', color="#E74C3C"
        )

        await ctx.send(embeds=embeds)

        # pager = Paginator(timeout=120, bot=self.bot, pages=embeds, paginator_behaviour=PaginatorBehaviour.disable)
        # pager.add_button("first", emoji="⏪", style=discord.ButtonStyle.blurple)
        # pager.add_button("previous", emoji="◀️", style=discord.ButtonStyle.blurple)
        # pager.add_button("goto", style=discord.ButtonStyle.green)
        # pager.add_button("next", emoji="▶️", style=discord.ButtonStyle.blurple)
        # pager.add_button("last", emoji="⏩", style=discord.ButtonStyle.blurple)
        # await pager.start_paginator(ctx)

    @commands.command()
    async def eval(self, ctx: commands.Context, *, code: str):
        if not code:
            if ctx.message.attachments:
                code = (await ctx.message.attachments[0].read()).decode()
            else:
                raise commands.MissingRequiredArgument(inspect.Parameter('code', inspect.Parameter.POSITIONAL_ONLY))

        code = clean_code(code)
        code = convert_code(code)

        stdout = io.StringIO()

        def new_print(*args, **kwargs):
            kwargs["file"] = stdout
            return print(*args, **kwargs)

        local_variables = {
            "_": self.last_result,
            "revolt": revolt,
            "commands": commands,
            "bot": self.client,
            "client": self.client,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.server,
            "server": ctx.server,
            "message": ctx.message,
            "print": new_print
        }

        try:
            exec(compile(code, "<repl>", "exec"), local_variables)

            async for obj in local_variables["func"]():
                await self.handle_send(ctx, obj)
                self.last_result = obj

            embeds = embed_creator(
                stdout.getvalue(), 3950, title="Code eval success", prefix='```py\n', suffix='```',
                color="blurple"
            )
            await ctx.message.add_reaction("✅")
        except Exception as e:
            result = "".join(format_exception(e, e, e.__traceback__))
            embeds = embed_creator(
                result, 3950, title="Code eval fail", prefix='```py\n', suffix='```', color="#E74C3C"
            )
            await ctx.message.add_reaction("❌")

        # await ctx.message.add_reaction("🔄")

        if not embeds:
            return

        return await ctx.send(embeds=embeds)

        # pager = Paginator(timeout=120, bot=self.bot, pages=embeds, paginator_behaviour=PaginatorBehaviour.disable)
        # pager.add_button("first", emoji="⏪", style=discord.ButtonStyle.blurple)
        # pager.add_button("previous", emoji="◀️", style=discord.ButtonStyle.blurple)
        # pager.add_button("goto", style=discord.ButtonStyle.green)
        # pager.add_button("next", emoji="▶️", style=discord.ButtonStyle.blurple)
        # pager.add_button("last", emoji="⏩", style=discord.ButtonStyle.blurple)
        #
        # await pager.start_paginator(ctx)


def setup(client):
    client.add_cog(Owner(client))
