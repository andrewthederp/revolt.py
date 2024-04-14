import asyncio

import aiohttp

import revolt
from revolt.ext import commands


class Client(commands.CommandsClient):
    async def get_prefix(self, message: revolt.Message):
        return "!"

    async def on_ready(self):
        print(f"{self.user.name} ({self.user.id}) is ready!")
        self.load_extension("cogs.owner")


async def main():
    async with aiohttp.ClientSession() as session:
        client = Client(session, "2ngRbZWRV2RWH8NgxJbuNXE8fgrakiu9ib--iK887I2TN43J8fFUveIKK3JmIUBO")
        await client.start()

asyncio.run(main())
