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
import requests
import sqlite3

import checks


with open('botsettings.json') as settings_file:
    settings = json.load(settings_file)


# TODO - Is WAL pragma needed to avoid DB contention between commands and background loop?

sql = sqlite3.connect('sql.db')
print('Loaded SQLite Database')
cur = sql.cursor()

## Create processedSubmissions table
sql.execute('CREATE TABLE IF NOT EXISTS ' \
    'processedSubmissions(' \
    'submissionID TEXT NOT NULL PRIMARY KEY, ' \
    'createdUTC INTEGER NOT NULL)')

## Create feeds table
sql.execute('CREATE TABLE IF NOT EXISTS ' \
    'feeds(' \
    'channelID TEXT NOT NULL PRIMARY KEY)')

## Create subscriptions table
sql.execute('CREATE TABLE IF NOT EXISTS ' \
    'subscriptions(' \
    'id INTEGER PRIMARY KEY, ' \
    'userID TEXT NOT NULL, ' \
    'matchPattern TEXT NOT NULL)')

sql.commit()


# Application info
username = settings["discord"]["description"]
version = '0.0.0'
print('{} - {}'.format(username, version))
start_time = datetime.datetime.utcnow()
default_embed_color = 0x669999
processedSubmissions = []


bot = commands.Bot(
    command_prefix=settings["discord"]["command_prefix"],
    description=settings["discord"]["description"]
)


@checks.admin_or_permissions(manage_server=True)
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


@checks.admin_or_permissions(manage_server=True)
@bot.command(pass_context=True, name="ping")
async def bot_ping(ctx):
    pong_message = await bot.say("Pong!")
    await asyncio.sleep(0.5)
    delta = pong_message.timestamp - ctx.message.timestamp
    millis = delta.days * 24 * 60 * 60 * 1000
    millis += delta.seconds * 1000
    millis += delta.microseconds / 1000
    await bot.edit_message(pong_message, "Pong! `{}ms`".format(int(millis)))


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


@checks.admin_or_permissions(manage_server=True)
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

def prettifySubs(username, rows):
    string = 'Subscriptions for user %s\n\n' % username
    for row in rows:
        string +=  str(row[0]) + ' ' + row[2] + '\n'
    return string

###################################
##### Subscription Management #####
###################################

@bot.command(pass_context=True, name="sub")
async def subscribe(ctx):
    command = ctx.message.content.split(' ', 1)

    # A valid sub command must be followed by a pattern like: !sub item
    if len(command) < 2:
        await bot.say("Invalid command. Display help or do nada")
    else:
        cur.execute('SELECT * FROM subscriptions WHERE userID=? and matchPattern=?',
                    (str(ctx.message.author.id), command[1]))
        if cur.fetchone():
            string = "User {} already has subscription to '{}'"
            await bot.say(string.format(ctx.message.author.name, command[1]))
        else:
            cur.execute('INSERT INTO subscriptions(userID, matchPattern) VALUES(?,?)',
                        (str(ctx.message.author.id), command[1]))
            sql.commit()
            string = "User {} successfully subscribed to '{}'"
            await bot.say(string.format(ctx.message.author.name, command[1]))

@bot.command(pass_context=True, name="unsub")
async def unsubscribe(ctx):
    command = ctx.message.content.split()

    if len(command) < 2:
        await bot.say("Invalid command. Display help or do nada")
    else:
        cur.execute('SELECT * FROM subscriptions WHERE id=? and userID=?',
                    (command[1], str(ctx.message.author.id)))
        if cur.fetchone():
            cur.execute('DELETE FROM subscriptions WHERE id=? and userID=?',
                        (command[1], str(ctx.message.author.id)))
            sql.commit()

            string = "{} has successfully unsubscribed from {}"
            await bot.say(string.format(ctx.message.author.name, command[1]))

        else:
            string = "User {} doesn't have subscription to '{}'"
            await bot.say(string.format(ctx.message.author, command[1]))

@bot.command(pass_context=True, name="unsuball")
async def unsubscribeAll(ctx):
    command = ctx.message.content.split()

    if len(command) != 1:
        await bot.say("Invalid command. Display help or do nada")
    else:
        cur.execute('SELECT * FROM subscriptions WHERE userID=?',
                    (str(ctx.message.author.id),))
        if cur.fetchone():
            cur.execute('DELETE FROM subscriptions WHERE userID=?',
                        (str(ctx.message.author.id),))
            sql.commit()

            string = "{} has successfully dropped all subscriptions"
            await bot.say(string.format(ctx.message.author.name))

        else:
            string = "User {} doesn't have any subscriptions"
            await bot.say(string.format(ctx.message.author))

@bot.command(pass_context=True, name="showsub")
async def showSubscription(ctx):
    command = ctx.message.content.split()

    if len(command) != 1:
        await bot.say("Invalid command. Display help or do nada")
    else:
        cur.execute('SELECT * FROM subscriptions WHERE userID=?',
                    (str(ctx.message.author.id),))

        string = prettifySubs(ctx.message.author.name, cur.fetchall())

        await bot.say(string)

######################################
##### Feed Processing/Management #####
######################################

@checks.admin_or_permissions(manage_server=True)
@bot.command(pass_context=True, name="addfeed")
async def addFeed(ctx):
    channelID = int(ctx.message.channel.id)
    channelName = ctx.message.channel.name
    cur.execute('SELECT channelID FROM feeds WHERE channelID=?',
                (channelID,))
    if cur.fetchone():
        embed=discord.Embed(
            title='❌ Feed already exists for channel **{}**' \
                  .format(channelName),
            color=0xDD2E44
        )
        await bot.say(embed=embed)
    else:
        cur.execute('INSERT INTO feeds VALUES(?)',
                    (channelID,))
        sql.commit()
        embed=discord.Embed(
            title='✅ Added feed to channel **{}**' \
                  .format(channelName),
            color=0x77B255
        )
        await bot.say(embed=embed)


@checks.admin_or_permissions(manage_server=True)
@bot.command(pass_context=True, name="removefeed")
async def removeFeed(ctx):
    channelID = int(ctx.message.channel.id)
    channelName = ctx.message.channel.name
    cur.execute('SELECT channelID FROM feeds WHERE channelID=?',
                (channelID,))
    if cur.fetchone():
        cur.execute('DELETE FROM feeds WHERE channelID=?',
                    (channelID,))
        sql.commit()
        embed=discord.Embed(
            title='✅ Removed feed from channel **{}**' \
                  .format(channelName),
            color=0x77B255
        )
        await bot.say(embed=embed)
    else:
        embed=discord.Embed(
            title='❌ No feeds found for channel **{}**' \
                  .format(channelName),
            color=0xDD2E44
        )
        await bot.say(embed=embed)


async def backgroundLoop():
    await bot.wait_until_ready()
    while bot.is_logged_in and not bot.is_closed:
        newSubmissionsFound = False
        r = requests.get(
            settings['feed']['json_url'],
            headers = {'User-agent': '{} - {}'.format(username, version)})
        subNew = r.json()
        for item in subNew['data']['children']:
            submissionID = str(item['data']['name'])
            submissionTitle = str(item['data']['title'])
            submissionURL = 'https://www.reddit.com' + \
                            str(item['data']['permalink'])
            submissionCreatedUTC = int(item['data']['created_utc'])
            cur.execute('SELECT submissionID FROM ' \
                        'processedSubmissions WHERE submissionID=?',
                        (submissionID,))
            if not cur.fetchone():
                newSubmissionsFound = True
                await pushToFeeds(submissionTitle, submissionURL)
                await pushToSubscriptions(submissionTitle, submissionURL)
                cur.execute('INSERT INTO processedSubmissions VALUES(?,?)',
                            (submissionID, submissionCreatedUTC))
                sql.commit()
        if newSubmissionsFound == True:
            cur.execute('DELETE FROM processedSubmissions ' \
                        'WHERE submissionID NOT IN ' \
                        '(SELECT submissionID FROM ' \
                        'processedSubmissions ' \
                        'ORDER BY createdUTC DESC LIMIT 50)')
            sql.commit()
            cur.execute('VACUUM')
            newSubmissionsFound = False
        await asyncio.sleep(300)


async def pushToFeeds(title, url):
    cur.execute('SELECT channelID from feeds')
    for row in cur:
        channelID = str(row[0])
        try:
            channel = bot.get_channel(id=channelID)
            await bot.send_message(
                        channel,
                        '**{}**\n<{}>\n-'.format(title, url)
                    )
        except discord.errors.NotFound as de:
            print('pushToFeeds : discord.errors.NotFound (Server/Channel) : ', de)
            pass
            # TODO - Delete feed if channel cannot be found?
        except Exception as e:
            print('pushToFeeds : ', e)
            pass
    await asyncio.sleep(0.1)


async def pushToSubscriptions(title, url):
    cur.execute('SELECT userID, matchPattern FROM subscriptions')
    for row in cur:
        userID = str(row[0])
        matchPattern = str(row[1]).lower().split(' ')
        if all([word in title.lower() for word in matchPattern]):
            try:
                user = bot.get_user_info(userID)
                await bot.send_message(
                            user,
                            '**{}**\n<{}>\n-'.format(title, url)
                        )
            except discord.errors.NotFound as de:
                print('pushToSubscriptions : discord.errors.NotFound (User) : ', de)
                pass
                # TODO - Delete user subscriptions if user cannot be found?
            except Exception as e:
                print('pushToSubscriptions : ', e)
                pass
    await asyncio.sleep(0.1)


bot.loop.create_task(backgroundLoop())
bot.run(settings["discord"]["client_token"])
