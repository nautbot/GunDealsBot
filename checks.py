from discord.ext import commands
import discord.utils

def check_permissions(ctx, perms):
    message = ctx.message
    channel = message.channel
    author = message.author
    resolved = channel.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())

def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True

    channel = ctx.message.channel
    author = ctx.message.author
    if channel.is_private:
        return False # can't have roles in PMs

    role = discord.utils.find(check, author.roles)
    return role is not None

def mod_or_permissions(**perms):
    def predicate(ctx):
        return role_or_permissions(ctx, lambda r: r.name in ('ServerAdmin', 'SpecialSnowflake'), **perms)

    return commands.check(predicate)

def admin_or_permissions(**perms):
    def predicate(ctx):
        return role_or_permissions(ctx, lambda r: r.name == 'ServerAdmin', **perms)

    return commands.check(predicate)