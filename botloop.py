import sys
import os
import math
import time
import datetime
import asyncio
import traceback
import json

import discord
from discord.ext import commands
import sqlite3


with open('botsettings.json') as settings_file:
    settings = json.load(settings_file)


# Application info
username = settings["discord"]["description"]
version = '0.0.0'
print('{} - {}'.format(username, version))
start_time = datetime.datetime.utcnow()
default_embed_color = 0x669999


bot = commands.Bot(
    command_prefix=settings["discord"]["command_prefix"],
    description=settings["discord"]["description"]
)


@bot.command(pass_context=True, name="test")
async def serve(ctx):
    await bot.say('test')


@bot.command(pass_context=True, name="restart")
async def bot_restart(ctx):
    try:
        print("Bot rebooted by {}".format(ctx.message.author.name))
        await bot.send_message(ctx.message.channel,
            '{} is restarting...'.format(username))
        await asyncio.sleep(2)
        await bot.logout()
        await asyncio.sleep(3)
        await bot.close()
        sys.exit(0)
    except Exception as e:
        print('bot_restart : ', e)
        pass
        sys.exit(0)

@bot.command(pass_context=True, name="ping")
async def bot_ping(ctx):
    await ctx.send('Pong! {0}'.format(round(bot.latency, 1)))


def get_bot_uptime(*, brief=False):
    now = datetime.datetime.utcnow()
    delta = now - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if not brief:
        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'
    else:
        fmt = '{h}h {m}m {s}s'
        if days:
            fmt = '{d}d ' + fmt
    return fmt.format(d=days, h=hours, m=minutes, s=seconds)


@bot.command(pass_context=True, name="status")
async def bot_status(ctx):
    passed = get_bot_uptime()
    embed=discord.Embed(
            title="Last Started:",
            description=start_time.strftime("%b %d, %Y at %I:%M:%S %p UTC"),
            color=default_embed_color
        )
    embed.add_field(name="Uptime:", value=passed, inline=False)
    embed.add_field(name="Version:", value=version, inline=False)
    await bot.say(embed=embed)
    print("Bot status requested by {}".format(ctx.message.author.name))


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.errors.CommandNotFound):
        pass  # ...don't need to know if commands don't exist
    if isinstance(error, commands.errors.CheckFailure):
        await bot.send_message(
            ctx.message.channel,
            '{} You don''t have permission to use this command.' \
            .format(ctx.message.author.mention))
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        formatter = commands.formatter.HelpFormatter()
        await bot.send_message(ctx.message.channel,
            '{} You are missing required arguments.\n{}'. \
            format(ctx.message.author.mention,
                formatter.format_help_for(ctx, ctx.command)[0]))
    elif isinstance(error, commands.errors.CommandOnCooldown):
        try:
            await bot.delete_message(ctx.message)
        except discord.errors.NotFound:
            pass
        message = await bot.send_message(
            ctx.message.channel, '{} This command was used {:.2f}s ago ' \
            'and is on cooldown. Try again in {:.2f}s.' \
            .format(ctx.message.author.mention,
                    error.cooldown.per - error.retry_after,
                    error.retry_after))
        await asyncio.sleep(10)
        await bot.delete_message(message)
    else:
        await bot.send_message(ctx.message.channel,
            'An error occured while processing the `{}` command.' \
            .format(ctx.command.name))
        print('Ignoring exception in command {0.command} ' \
            'in {0.message.channel}'.format(ctx))
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        print(''.join(tb))


@bot.event
async def on_error(event_method, *args, **kwargs):
    if isinstance(args[0], commands.errors.CommandNotFound):
        # for some reason runs despite the above
        return
    print('Ignoring exception in {}'.format(event_method))
    mods_msg = "Exception occured in {}".format(event_method)
    tb = traceback.format_exc()
    print(''.join(tb))
    mods_msg += '\n```' + ''.join(tb) + '\n```'
    mods_msg += '\nargs: `{}`\n\nkwargs: `{}`'.format(args, kwargs)
    print(mods_msg)
    print(args)
    print(kwargs)


@bot.event
async def on_ready():
    await asyncio.sleep(1)
    print("Logged in to discord.")
    try:
        await bot.change_presence(
            game=discord.Game(name=settings["discord"]["game"]),
            status=discord.Status.online,
            afk=False)
    except Exception as e:
        print('on_ready : ', e)
        pass
    await asyncio.sleep(1)

@bot.command(pass_context=True, name="sub")
async def subscribe(ctx):
    print(dir(ctx))
    command = ctx.message.content.split()
    
    if len(command) < 2:
        await bot.say("Invalid command. Display help or do nada")
    else:
        string = "{} has successfully subscribed to {}"
        await bot.say(string.format(ctx.message.author, command[1]))

    # TODO - Write 1 new record to db with fields [userid, subscription string] if it doesn't exist

@bot.command(pass_context=True, name="unsub")
async def unsubscribe(ctx):
    print(dir(ctx))
    command = ctx.message.content.split()
    
    if len(command) < 2:
        await bot.say("Invalid command. Display help or do nada")
    else:
        string = "{} has successfully unsubscribed from {}"
        await bot.say(string.format(ctx.message.author, command[1]))

    # TODO - Remove 1 record from db matching [userid, subscription string] if it exists

@bot.command(pass_context=True, name="unsuball")
async def unsubscribeAll(ctx):
    print(dir(ctx))
    command = ctx.message.content.split()
   
    string = "{} has successfully dropped all subscriptions"
    await bot.say(string.format(ctx.message.author))

    # TODO - Remove [0, many] records from db matching [userid] if any exist

@bot.command(pass_context=True, name="showsub")
async def showSubscription(ctx):
    print(dir(ctx))
    command = ctx.message.content.split()
   
    string = "Gundeals subscriptions for {}: ..."
    await bot.say(string.format(ctx.message.author))

    # TODO - Retrieve [0, many] records from db matching [userid] if any exist
bot.run(settings["discord"]["client_token"])
