import hikari.intents
from common.models.message_command_parsing import *
from common.gateways import BOT
import hikari
import arc
import miru
import os
from commands import *

discord_msg_command_parser = (CommandParserBuilder()
    .with_commands(CREATED_COMMANDS)
    .with_string_converter(StringConverter())
    .build())


@BOT.listen(hikari.GuildMessageCreateEvent)
async def parse_message_command(msg: hikari.GuildMessageCreateEvent):
    if msg.is_bot or not msg.content:
        return 

    try:
        await discord_msg_command_parser.parse(msg.message.content, msg)
    except Exception as e:
        await msg.message.respond(e)
BOT.run()