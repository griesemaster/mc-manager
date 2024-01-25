
import os
import sys
import discord
import time
import subprocess
import logging
import logging.handlers
import requests
import paramiko as pm
from discord.ext import commands
from dotenv import load_dotenv
from shell import shell

#LOGGING SETUP
logfile = 'logs/manager.log'
log = logging.getLogger()
log.setLevel(logging.INFO)

logFormat = logging.Formatter('%(asctime)s\t%(name)s:\t%(levelname)s:\t %(message)s', datefmt='%m-%d-%Y %I:%M:%S')

fileHandler = logging.handlers.RotatingFileHandler(logfile, mode='w', backupCount=5)
fileHandler.setLevel(logging.INFO)
fileHandler.setFormatter(logFormat)

stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setLevel(logging.INFO)
stdoutHandler.setFormatter(logFormat)

log.addHandler(fileHandler)
log.addHandler(stdoutHandler)

should_rollover_logfile = os.path.isfile(logfile)
if should_rollover_logfile:
    fileHandler.doRollover()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#SETUP DISCORD CLIENT
intents = discord.Intents(guilds=True,guild_messages=True, message_content=True, guild_reactions=True)
bot = commands.Bot(intents = intents, command_prefix='!', status='idle')

VALID_GAME_TYPES = ['minecraft', 'palworld']

def get_ip():
    return requests.get('https://api.ipify.org').content.decode('utf8')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('Command on a %.2fs cooldown!' % error.retry_after)
    raise error

@commands.cooldown(1, 5, commands.BucketType.default)
@bot.command(name='list', aliases=['users', 'online'])
async def show_online_players(ctx):
    """Shows a report of current online users"""
    await ctx.send(shell().list())

@commands.cooldown(1, 20, commands.BucketType.default)
@bot.command(name='start', aliases=['wake', 'begin', 'turnon', 'on', 'arouse'])
async def start_server(ctx, game_type):
    """Wakes remote and launches minecraft server"""
    await bot.change_presence(status='online', activity=discord.Game(name=f'Minecraft on {get_ip()}'))
    await ctx.message.add_reaction('\U0001F504')
    assert game_type in VALID_GAME_TYPES, f'Valid game types are: {VALID_GAME_TYPES}'
    shell().start_server(game_type)
    if shell().is_server_online():
        await ctx.send('Online @'+ get_ip())
    await ctx.message.add_reaction('\U00002705')

@commands.cooldown(1, 20, commands.BucketType.default)
@bot.command(name='sleep', aliases=['stop', 'quit', 'shutdown', 'off']) 
async def sleep_remote(ctx):
    """Kills the current server then sleeps remote"""
    if not shell().is_server_online():
        await ctx.send('Server already sleeping!')  
    else:
        await ctx.message.add_reaction('\U0001F504')
        await ctx.message.add_reaction('\U0001F634')
        await bot.change_presence(status='idle', activity=None)
        shell().stop_server()
    await ctx.message.add_reaction('\U00002705')


bot.run(TOKEN)

