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

from EmbedField import EmbedField

with open('botsettings.json') as settings_file:
    settings = json.load(settings_file)


sql = sqlite3.connect('sql.db', check_same_thread=False)
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
MAX_SUBSCRIPTIONS = 25


bot = commands.Bot(
    command_prefix=settings["discord"]["command_prefix"],
    description=settings["discord"]["description"]
)

# Remove default help command so we can customise
bot.remove_command('help')

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
    lastStarted=start_time.strftime("%b %d, %Y at %I:%M:%S %p UTC")

    lastStartedField = EmbedField(name="Last Started:", value=lastStarted, inline=False)
    uptimeField = EmbedField(name="Uptime:", value=passed, inline=False)
    versionField = EmbedField(name="Version:", value=version, inline=False)
    fieldList = [lastStartedField, uptimeField, versionField]

    embed = embedInformation(title="Bot Status", fieldList=fieldList)
    await bot.say(embed=embed)

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

def embedError(title, description=''):
    em = discord.Embed(
        title='❌ {}'.format(title),
        description='%s' % description,
        color=0xDD2E44
    )
    em.set_footer(text="This is an error message.")
    return em

def embedSuccess(title, description=''):
    em = discord.Embed(
        title='✅ {}'.format(title),
        description='%s' % description,
        color=0x77B255
    )
    em.set_footer(text="This is a success message.")
    return em

def embedInformation(title, fieldList=None, description=''):
    em = discord.Embed(
        title='ℹ️ {}'.format(title),
        description='%s' % description,
        color=0x0079D8,
        )

    if fieldList is not None:
        for field in fieldList:
            em.add_field(name=field._name, value=field._value, inline=field._inline)

    em.set_footer(text="This is an informational message.")
    return em

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
        ###############################################
        # Check if user already has this subscription #
        ###############################################
        cur.execute('SELECT * FROM subscriptions WHERE userID=? and matchPattern=?',
                    (str(ctx.message.author.id), command[1]))
        if cur.fetchone():
            string = "User {} already has subscription to '{}'" \
                .format(ctx.message.author.name, command[1])
            embed = embedInformation(title=string)
            await bot.say(embed=embed)
            return

        #####################################
        # Get count of user's subscriptions #
        #####################################
        cur.execute('SELECT count(*) FROM subscriptions WHERE userID=?',
                    (str(ctx.message.author.id),))
        numRecords = cur.fetchone()[0]

        if numRecords == MAX_SUBSCRIPTIONS:
            title = "User {} already has max number of subscriptions ({})." \
                .format(ctx.message.author.name, MAX_SUBSCRIPTIONS)
            description = "Run {0}unsub <ID> command to free a slot. \n\nThen try {0}sub <ID>" \
                .format(settings["discord"]["command_prefix"])
            embed = embedInformation(title=title, description=description)
            await bot.say(embed=embed)
            return

        ############################
        # Create new subscriptions #
        ############################
        cur.execute('INSERT INTO subscriptions(userID, matchPattern) VALUES(?,?)',
                    (str(ctx.message.author.id), command[1]))
        sql.commit()
        string = "User {} successfully subscribed to '{}'" \
            .format(ctx.message.author.name, command[1])

        embed = embedSuccess(title=string)
        await bot.say(embed=embed)

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

            string = "{} has successfully unsubscribed from {}" \
                .format(ctx.message.author.name, command[1])
            embed = embedSuccess(title=string)
            await bot.say(embed=embed)

        else:
            string = "User {} doesn't have subscription to '{}'" \
                .format(ctx.message.author, command[1])
            embed = embedInformation(title=string)
            await bot.say(embed=embed)

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

            string = "{} has successfully dropped all subscriptions" \
                .format(ctx.message.author.name)
            embed = embedSuccess(title=string)
            await bot.say(embed=embed)

        else:
            string = "User {} doesn't have any subscriptions" \
                .format(ctx.message.author)
            embed = embedInformation(title=string)
            await bot.say(embed=embed)

@bot.command(pass_context=True, name="showsub")
async def showSubscription(ctx):
    command = ctx.message.content.split()

    if len(command) != 1:
        await bot.say("Invalid command. Display help or do nada")
    else:
        # Get number of subscriptions
        cur.execute('SELECT count(*) FROM subscriptions WHERE userID=?',
                    (str(ctx.message.author.id),))
        numRecords = cur.fetchone()[0]

        # Get subscriptions
        cur.execute('SELECT id, matchPattern FROM subscriptions WHERE userID=?',
                    (str(ctx.message.author.id),))

        fieldList = list()
        for row in cur:
            string = "{}) {}".format(row[0], row[1])

            # '\u200b' is a zero width space. This is used when we don't want
            # a name in an embed field
            field = EmbedField(value='\u200b', name=string, inline=False)
            fieldList.append(field)

        title = "Subscriptions for user %s" % ctx.message.author.name
        description = "User has %d subscriptions." % numRecords
        embed = embedInformation(title=title, fieldList=fieldList, description=description)
        await bot.say(embed=embed)

@bot.command(pass_context=True, name="help")
async def help(ctx):
    command = ctx.message.content.split()

    if len(command) != 1:
        await bot.say("Invalid command. Display help or do nada")
    else:
        title = "Available commands for gundeals bot"
        #settings["discord"]["command_prefix"]


        fieldSub = EmbedField(value='Subscribe to a matchPattern to be notified of deals matching pattern',
            name="sub <matchPattern>",
            inline=False)

        fieldUnsub = EmbedField(value='Unsubscribe from a matchPattern', name="unsub <subId>", inline=False)
        fieldUnsuball = EmbedField(value='Unsubscribe from all subscriptions', name="unsuball", inline=False)
        fieldShowsub = EmbedField(value='Show your current subscriptions in form: [subId] [matchPattern]', name="showsub", inline=False)
        fieldList = list((fieldSub, fieldUnsub, fieldUnsuball, fieldShowsub))
        embed = embedInformation(title=title, fieldList=fieldList)
        await bot.say(embed=embed)

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
        string = "Feed already exists for channel **{}**" \
            .format(channelName)
        embed = embedInformation(string)
        await bot.say(embed=embed)
    else:
        cur.execute('INSERT INTO feeds VALUES(?)',
                    (channelID,))
        sql.commit()

        string = "Added feed to channel **{}**" \
              .format(channelName)
        embed = embedSuccess(string)
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

        string = "Removed feed from channel **{}**" \
              .format(channelName)
        embed = embedSuccess(string)
        await bot.say(embed=embed)

    else:
        string = "No feeds found for channel **{}**" \
              .format(channelName)
        embed = embedError(string)
        await bot.say(embed=embed)


async def backgroundLoop():
    await bot.wait_until_ready()
    while bot.is_logged_in and not bot.is_closed:
        newSubmissionsFound = False
        headers = {'User-agent': '{} - {}'.format(username, version)}
        r = requests.get(settings['feed']['json_url'],
                         headers=headers)
        subNew = r.json()
        for item in subNew['data']['children']:
            submissionID = str(item['data']['name'])
            submissionTitle = str(item['data']['title'])
            submissionCreatedUTC = int(item['data']['created_utc'])
            submissionURL = 'https://www.reddit.com/' + \
                            str(item['data']['id'])
            thumbnailURL = (str(item['data']['thumbnail']) \
                           if str(item['data']['thumbnail']) != 'default' \
                           else 'https://i.imgur.com/RMbd1PC.png')
            cur.execute('SELECT submissionID ' \
                        'FROM processedSubmissions ' \
                        'WHERE submissionID=?',
                        (submissionID,))
            if not cur.fetchone():
                newSubmissionsFound = True
                await pushToFeeds(submissionTitle,
                                  submissionURL)
                await pushToSubscriptions(submissionTitle,
                                          submissionURL,
                                          thumbnailURL)
                cur.execute('INSERT INTO processedSubmissions VALUES(?,?)',
                            (submissionID, submissionCreatedUTC))
                sql.commit()
        if newSubmissionsFound == True:
            cur.execute('DELETE FROM processedSubmissions ' \
                        'WHERE submissionID NOT IN ' \
                        '(SELECT submissionID ' \
                        'FROM processedSubmissions ' \
                        'ORDER BY createdUTC DESC LIMIT 50)')
            sql.commit()
            cur.execute('VACUUM')
            newSubmissionsFound = False
        await asyncio.sleep(300)


async def pushToFeeds(title, url):
    feedItem = '**{}**\n<{}>\n-'.format(title, url)
    cur.execute('SELECT channelID from feeds')
    for row in cur:
        channelID = str(row[0])
        try:
            channel = bot.get_channel(id=channelID)
            await bot.send_message(channel, feedItem)
        except discord.errors.NotFound as de:
            print('pushToFeeds : ' \
                  'discord.errors.NotFound ' \
                  '(Server/Channel) : ', de)
            pass
        except Exception as e:
            print('pushToFeeds : ', e)
            pass
    await asyncio.sleep(0.1)


async def pushToSubscriptions(title, url, thumbnailURL):
    cur.execute('SELECT ID, userID, matchPattern ' \
                'FROM subscriptions')
    for row in cur:
        matchPattern = str(row[2]).lower().split(' ')
        if all([word in title.lower() for word in matchPattern]):
            subscriptionID = str(row[0])
            userID = str(row[1])
            try:
                user = bot.get_user_info(userID)
            except discord.errors.NotFound as de:
                print('pushToSubscriptions : ' \
                     'discord.errors.NotFound (User) : ', de)
                pass
            except Exception as e:
                print('pushToSubscriptions : ', e)
                pass
            # field = EmbedField(name='**{}**'.format(url),
            #     value='Reply with **{}unsub {}** ' \
            #            'to cancel this subscription.' \
            #            .format(settings["discord"]["command_prefix"],
            #                    subscriptionID),
            #     inline=False)
            # fieldList = [field]
            # embed = embedInformation(title='**New post found matching ' \
            #     'your subscription "{}"!**' \
            #     .format(matchPattern),
            #     fieldList=fieldList,
            #     description=title)
            # embed.set_thumbnail(url=thumbnailURL)
            embed = discord.Embed(
                title='**New post found matching ' \
                      'your subscription "{}"!**' \
                      .format(matchPattern),
                description=title,
                color=0x0079D8)
            embed.set_thumbnail(url=thumbnailURL)
            embed.add_field(name='**{}**'.format(url),
                value='Reply with **{}unsub {}** ' \
                       'to cancel this subscription.' \
                       .format(settings["discord"]["command_prefix"],
                               subscriptionID),
                inline=False)
            await bot.send_message(user, embed=embed)
    await asyncio.sleep(0.1)


bot.loop.create_task(backgroundLoop())
bot.run(settings["discord"]["client_token"])
