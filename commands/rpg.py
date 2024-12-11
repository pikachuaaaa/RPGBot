import hikari
from common.gateways import *
from common.models.message_command_parsing import Command

@Command("!rpg","ping!")
async def ping(ctx: hikari.GuildMessageCreateEvent):
    await ctx.message.respond(f'pong!')


