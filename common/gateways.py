import hikari
import miru
import arc
import os

BOT = hikari.GatewayBot(os.environ["RPGbot"], intents=hikari.Intents.ALL)
MCL = miru.Client(BOT)
REGISTRED_GUILDS = [866366097242325012]
ACL = arc.GatewayClient(BOT, default_enabled_guilds=REGISTRED_GUILDS)
client = arc.GatewayClient(BOT)