# sglobbylink-discord.py
# by Mr Peck (2018-2020)
# project page: https://github.com/itsmrpeck/sglobbylink-discord.py

# IMPORTANT: You must enter your Discord bot token and Steam API key in settings_sglobbylink.py or the bot won't work!

import discord
import asyncio
import json
import aiohttp
import threading
import time
from discord.ext import tasks
from itertools import cycle
from enum import Enum
from settings_sglobbylink import *

# Default settings for old versions of settings_sglobbylink:
if not "allowImagePosting" in locals():
    allowImagePosting = True

if not "imagePostingCooldownSeconds" in locals():
    imagePostingCooldownSeconds = 60 * 10

if discordBotTokenIMPORTANT == "PASTE_DISCORD_BOT_TOKEN_HERE":
    print("ERROR: Discord bot token has not been set. Get one from https://discordapp.com/developers/applications/me and paste it into 'discordBotTokenIMPORTANT' in settings_sglobbylink.py")
    quit()

if steamApiKeyIMPORTANT == "PASTE_STEAM_API_KEY_HERE":
    print("ERROR: Steam Web API key has not been set. Get one from https://steamcommunity.com/dev/apikey and paste it into 'steamApiKeyIMPORTANT' in settings_sglobbylink.py")
    quit()


versionNumber = "1.4"

steamProfileUrlIdentifier = "steamcommunity.com/id"
steamProfileUrlIdentifierLen = len(steamProfileUrlIdentifier)

steamProfileUrlLongIdentifier = "steamcommunity.com/profiles"
steamProfileUrlLongIdentifierLen = len(steamProfileUrlLongIdentifier)

steamIdTable = {}

steamIdInstructionsOnlyFullURL = "예시와 같이 입력해주세요. '~저장 https://steamcommunity.com/profiles/76561198119856587/' or '~저장 https://steamcommunity.com/id/PAUZEE/'"
steamIdInstructionsPartialURLAllowed = "전체 스팀 프로필주소를 입력해주세요. '~저장 https://steamcommunity.com/profiles/76561198119856587/' or '~저장 https://steamcommunity.com/id/PAUZEE/'"

todaysRequestCounts = {}

todaysTotalRequestCount = 0

requestCountsLock = threading.RLock()

lastPublicProfileImagePostedTimestamp = 0
lastSteamURLImagePostedTimestamp = 0

client = discord.Client()

class RequestLimitResult(Enum):
    LIMIT_NOT_REACHED = 1
    USER_LIMIT_JUST_REACHED = 2
    TOTAL_LIMIT_JUST_REACHED = 3
    ALREADY_OVER_LIMIT = 4

class LobbyBotCommand(Enum):
    NONE = 1
    HELP = 2
    STEAMID = 3
    LOBBY = 4

def get_steam_id_instructions():
    if onlyAllowFullProfileURLs:
        return steamIdInstructionsOnlyFullURL
    else:
        return steamIdInstructionsPartialURLAllowed

async def save_steam_ids():
    try:
        with open(steamIdFileName, 'w+') as f:
            for discordUserId in steamIdTable.keys():
                f.write(str(discordUserId) + " " + steamIdTable[discordUserId] + "\n")
    except:
        pass

async def load_steam_ids():
    global steamIdFileName
    global steamIdTable

    try:
        with open(steamIdFileName, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                splitLine = line.split(" ")
                if len(splitLine) >= 2:
                    steamIdTable[int(splitLine[0])] = splitLine[1]
    except:
        pass

def increment_request_count(userIdInt): # returns whether or not the user has hit their daily request limit
    global todaysRequestCounts
    global todaysTotalRequestCount
    global maxDailyRequestsPerUser
    global maxTotalDailyRequests

    if maxDailyRequestsPerUser <= 0:
        return RequestLimitResult.ALREADY_OVER_LIMIT

    with requestCountsLock:

        if todaysTotalRequestCount > maxTotalDailyRequests:
            return RequestLimitResult.ALREADY_OVER_LIMIT

        if userIdInt not in todaysRequestCounts.keys():
            todaysRequestCounts[userIdInt] = 0

        if todaysRequestCounts[userIdInt] > maxDailyRequestsPerUser:
            return RequestLimitResult.ALREADY_OVER_LIMIT

        todaysRequestCounts[userIdInt] += 1
        todaysTotalRequestCount += 1

        if todaysTotalRequestCount > maxTotalDailyRequests:
            return RequestLimitResult.TOTAL_LIMIT_JUST_REACHED

        elif todaysRequestCounts[userIdInt] > maxDailyRequestsPerUser:
            return RequestLimitResult.USER_LIMIT_JUST_REACHED

        else:
            return RequestLimitResult.LIMIT_NOT_REACHED

    return RequestLimitResult.ALREADY_OVER_LIMIT


async def clear_request_counts_once_per_day():
    global todaysRequestCounts
    global todaysTotalRequestCount

    await client.wait_until_ready()
    while not client.is_closed():
        with requestCountsLock:
            todaysRequestCounts.clear()
            todaysTotalRequestCount = 0
        await asyncio.sleep(60*60*24) # task runs every 24 hours

def check_if_public_profile_image_can_be_posted_and_update_timestamp_if_true():
    global allowImagePosting
    global imagePostingCooldownSeconds
    global lastPublicProfileImagePostedTimestamp

    if allowImagePosting:
        currentTime = time.time()
        if (currentTime - lastPublicProfileImagePostedTimestamp) >= imagePostingCooldownSeconds:
            lastPublicProfileImagePostedTimestamp = currentTime
            return True

    return False

def check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
    global allowImagePosting
    global imagePostingCooldownSeconds
    global lastSteamURLImagePostedTimestamp

    if allowImagePosting:
        currentTime = time.time()
        if (currentTime - lastSteamURLImagePostedTimestamp) >= imagePostingCooldownSeconds:
            lastSteamURLImagePostedTimestamp = currentTime
            return True

    return False

async def async_get_json(url): 
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                return None

status = cycle(["~플매", "~저장", "~주소"])

@client.event
async def on_ready():
    await load_steam_ids()
    client.loop.create_task(clear_request_counts_once_per_day())
    print("LOADED: sglobbylink-discord.py v" + versionNumber + " by Mr Peck.")
    await client.get_channel(867596676705026088).send("플매봇 동작시작")
    change_status.start()
    send_message.start()

@tasks.loop(seconds=5)  
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))

x = 20

@tasks.loop(minutes=x)
async def send_message():
    await client.get_channel(867596676705026088).send("~주소")
    await client.get_channel(867596676705026088).send("~채팅청소 3")

@client.event
async def on_message(message):

    if message.content.startswith("~채팅청소"):
        if message.author.guild_permissions.manage_messages:
            try:
                amount = message.content[6:]
                await message.channel.purge(limit=1)
                await message.channel.purge(limit=int(amount))
                await message.channel.send(f"**{amount}**개의 메시지를 지웠습니다.")
            except ValueError:
                await message.channel.send("청소하실 메시지의 **수**를 입력해 주세요.")
        else:
            await message.channel.send("권한이 없습니다.")



    # all commands start with '!', but we try to handle messages that start with <@ too
    if not message.content.startswith('~') and not message.content.startswith('<@'):
        return

    messageContent = message.content[:40] # Grab enough message for an @username and some whitespace before the !command

    # If we start with a <@, skip everything up to the >
    startedWithUsername = messageContent.startswith('<@')
    if startedWithUsername:
        whitespaceStart = messageContent.find('>')
        if whitespaceStart > 0:
            messageContent = messageContent[(whitespaceStart + 1):]
        else:
            return # We didn't find a '>'

    # Skip leading whitespace
    messageContent =  messageContent.lstrip()

    # all commands start with '!'
    if not messageContent.startswith('~'):
        return

    # filter out DMs
    if not allowDirectMessages and not message.channel:
        return

    # filter out messages not on the whitelisted channels
    if channelWhitelistIDs and message.channel:
        channelFound = False
        for channelID in channelWhitelistIDs:
            if message.channel.id == (int(channelID) if isinstance(channelID, str) else channelID):
                channelFound = True
                break
        if not channelFound:
            return

    # check which command we wanted (and ignore any message that isn't a command)
    lowerCaseMessageStart = messageContent[:8].lower()
    if lowerCaseMessageStart.startswith('~플매') and not startedWithUsername:
        botCmd = LobbyBotCommand.HELP
    elif lowerCaseMessageStart.startswith('~저장') and not startedWithUsername:
        botCmd = LobbyBotCommand.STEAMID
    elif lowerCaseMessageStart.startswith('~주소'):
        botCmd = LobbyBotCommand.LOBBY
    else:
        return

    # rate limit check
    rateLimitResult = increment_request_count(message.author.id)
    if rateLimitResult == RequestLimitResult.ALREADY_OVER_LIMIT:
        return
    elif rateLimitResult == RequestLimitResult.TOTAL_LIMIT_JUST_REACHED:
        await message.channel.send("Error: Total daily bot request limit reached. Try again in 24 hours.")
        return
    elif rateLimitResult == RequestLimitResult.USER_LIMIT_JUST_REACHED:
        await message.channel.send("Error: Daily request limit reached for user " + message.author.name + ". Try again in 24 hours.")
        return

    # actually execute the command
    if botCmd == LobbyBotCommand.HELP:
        await message.channel.send("플매봇 입니다.\n\nCommands:\n- `~주소`: 초대링크를 대화방에 보냅니다.\n- `~저장`: 프로필주소를 저장합니다.\n" + get_steam_id_instructions())
        if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
            await message.channel.send("", file=discord.File("steam.jpg"))
        return

    elif botCmd == LobbyBotCommand.STEAMID:
        words = message.content.split(" ")
        bSavedSteamId = False
        if len(words) < 2:
            await message.channel.send("`~저장`: " + get_steam_id_instructions())
            if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                await message.channel.send("", file=discord.File("steam.jpg"))
            return
        else:
            maxWordCount = min(len(words), 10)
            idStr = ""
            for i in range(1, maxWordCount):
                if len(words[i]) > 0:
                    idStr = words[i]
                    break

            idStr = idStr.rstrip('/')

            profileUrlStart = idStr.find(steamProfileUrlIdentifier)
            if profileUrlStart != -1:
                # It's a steam profile URL. Erase everything after the last slash
                lastSlash = idStr.rfind('/')
                if lastSlash >= (profileUrlStart + steamProfileUrlIdentifierLen):
                    idStr = idStr[lastSlash + 1:]
                else:
                    # This is a malformed profile URL, with no slash after "steamcommunity.com/id"
                    await message.channel.send("~저장: " + get_steam_id_instructions())
                    if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                        await message.channel.send("", file=discord.File("steam.jpg"))
                    return
            else:
                # Try the other type of steam profile URL. Let's copy and paste.
                profileUrlStart = idStr.find(steamProfileUrlLongIdentifier)

                if profileUrlStart != -1:
                    # It's a steam profile URL. Erase everything after the last slash
                    lastSlash = idStr.rfind('/')
                    if lastSlash >= (profileUrlStart + steamProfileUrlLongIdentifierLen):
                        idStr = idStr[lastSlash + 1:]
                    else:
                        # This is a malformed profile URL, with no slash after "steamcommunity.com/profiles"
                        await message.channel.send("~저장: " + get_steam_id_instructions())
                        if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                            await message.channel.send("", file=discord.File("steam.jpg"))
                        return
                elif onlyAllowFullProfileURLs:
                    # This isn't either type of full profile URL, and we're only allowing full profile URLs
                    await message.channel.send("~저장" + get_steam_id_instructions())
                    if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                        await message.channel.send("", file=discord.File("steam.jpg"))
                    return

            if len(idStr) > 200:
                await message.channel.send("아이디가 길이가 너무 깁니다.")
                return
            else:
                steamIdUrl = "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=" + steamApiKeyIMPORTANT + "&vanityurl=" + idStr
                contents = await async_get_json(steamIdUrl)
                if contents:
                    data = json.loads(contents)
                    if data["response"] is None:
                        await message.channel.send("SteamAPI: ResolveVanityURL() failed for " + message.author.name + ". Is the Steam Web API down?")
                        return
                    else:
                        if "steamid" in data["response"].keys():
                            steamIdTable[message.author.id] = data["response"]["steamid"]
                            await save_steam_ids()
                            await message.channel.send(message.author.name + " 님의 프로필 주소가 저장되었습니다.")
                            bSavedSteamId = True
                            # Don't return; fall through to the "if bSavedSteamId" code instead
                        elif idStr.isdigit():
                            steamIdTable[message.author.id] = idStr
                            await save_steam_ids()
                            await message.channel.send(message.author.name + " 님의 프로필 주소가 저장되었습니다.")
                            bSavedSteamId = True
                            # Don't return; fall through to the "if bSavedSteamId" code instead
                        else:
                            await message.channel.send("Could not find Steam ID: " + idStr + ". Make sure you " + get_steam_id_instructions())
                            if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                                await message.channel.send("", file=discord.File("steam.jpg"))
                            return
                else:
                    await message.channel.send(message.author.name + " 님의 저장된 주소를 찾을수 없습니다. 저장을 먼저 해주세요.")
                    return

        if bSavedSteamId:
            # It's common for players to add themselves to the bot without their Steam Game Details being public. Tell them this right away, to save time
            if message.author.id in steamIdTable.keys():
                steamId = steamIdTable[message.author.id]
                profileUrl = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=" + steamApiKeyIMPORTANT + "&steamids=" + steamId
                contents = await async_get_json(profileUrl)
                if contents:
                    data = json.loads(contents)
                    if "response" in data.keys():
                        pdata = data["response"]["players"][0]
                        if "lobbysteamid" not in pdata.keys():
                            # Steam didn't give us a lobby ID. But why?
                            # Let's test if their profile's Game Details are public by seeing if Steam will tell us how many games they own.
                            ownedGamesUrl = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=" + steamApiKeyIMPORTANT + "&steamid=" + steamId + "&include_played_free_games=1"
                            ownedGamesContents = await async_get_json(ownedGamesUrl)
                            if ownedGamesContents:
                                ownedGamesData = json.loads(ownedGamesContents)
                                if "response" in ownedGamesData.keys():
                                    if not ("game_count" in ownedGamesData["response"].keys() and ownedGamesData["response"]["game_count"] > 0):
                                        await message.channel.send(message.author.name + "님의 '게임 세부정보'가 공개 상태가 아닙니다.)")
                                        if check_if_public_profile_image_can_be_posted_and_update_timestamp_if_true():
                                            await message.channel.send("", file=discord.File("steam.jpg"))
        return

    elif botCmd == LobbyBotCommand.LOBBY:
        if message.author.id in steamIdTable.keys():
            steamId = steamIdTable[message.author.id]
            profileUrl = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=" + steamApiKeyIMPORTANT + "&steamids=" + steamId
            contents = await async_get_json(profileUrl)
            if contents:
                data = json.loads(contents)
                if "response" in data.keys():
                    pdata = data["response"]["players"][0]
                    if "lobbysteamid" in pdata.keys():
                        steamLobbyUrl = "steam://joinlobby/" + pdata["gameid"] + "/" + pdata["lobbysteamid"] + "/" + steamId
                        gameName = ""
                        if "gameextrainfo" in pdata.keys():
                            gameName = pdata["gameextrainfo"] + " "
                        await message.channel.send(message.author.name + "님의 " + gameName + "방: " + steamLobbyUrl)
                        return
                    else:
                        # Steam didn't give us a lobby ID. But why?
                        # Let's test if their profile's Game Details are public by seeing if Steam will tell us how many games they own.
                        ownedGamesUrl = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=" + steamApiKeyIMPORTANT + "&steamid=" + steamId + "&include_played_free_games=1"
                        ownedGamesContents = await async_get_json(ownedGamesUrl)
                        if ownedGamesContents:
                            ownedGamesData = json.loads(ownedGamesContents)
                            if "response" in ownedGamesData.keys():
                                if "game_count" in ownedGamesData["response"].keys() and ownedGamesData["response"]["game_count"] > 0:
                                    # They have public Game Details. Let's make sure we can see their account, and that they're online
                                    if pdata["communityvisibilitystate"] == 3: # If the bot can view whether or not the player's Steam account is online https://developer.valvesoftware.com/wiki/Steam_Web_API#GetPlayerSummaries_.28v0002.29
                                        if "personastate" in pdata.keys() and pdata["personastate"] > 0:
                                            # They have public Game Details, Steam thinks they're online. Let's see if they're in a game!
                                            if "gameid" in pdata.keys():
                                                gameName = ""
                                                if "gameextrainfo" in pdata.keys():
                                                    gameName = pdata["gameextrainfo"]
                                                else:
                                                    gameName = "a game"
                                                await message.channel.send(message.author.name + " 님의 방을 찾을 수 없습니다. " +  gameName + "에(는) 있지만 있지만 방을 생성하지 않았습니다.")
                                                return
                                            else:
                                                await message.channel.send(message.author.name + " 님의 방을 찾을 수 없습니다. " " : 스팀 온라인 상태이지만 게임을 실행하지 않았습니다.")
                                                return
                                        else:
                                            await message.channel.send(message.author.name + " 님의 방을 찾을 수 없습니다. " + message.author.name + ": 스팀 오프라인 상태입니다.")
                                            return
                                    else:
                                        await message.channel.send(message.author.name + " 님의 방을 찾을 수 없습니다. " ": '나의 프로필'이 공개 상태가 아닙니다. 공개 상태로 바꿔주세요")
                                        if check_if_public_profile_image_can_be_posted_and_update_timestamp_if_true():
                                            await message.channel.send("", file=discord.File("steam.jpg"))
                                        return
                                else:
                                    await message.channel.send(message.author.name + " 님의 방을 찾을 수 없습니다. " ": '게임세부정보' 가 공개 상태가 아닙니다.")
                                    if check_if_public_profile_image_can_be_posted_and_update_timestamp_if_true():
                                        await message.channel.send("", file=discord.File("steam.jpg"))
                                    return
                            else:
                                await message.channel.send("SteamAPI: GetOwnedGames() failed for " + message.author.name + ". Is the Steam Web API down?")
                                return
                        else:
                            await message.channel.send("SteamAPI: GetOwnedGames() failed for " + message.author.name + ". Is the Steam Web API down?")
                            return
                else:
                    await message.channel.send("SteamAPI: GetPlayerSummaries() failed for " + message.author.name + ". Is the Steam Web API down?")
                    return
                        
            else:
                await message.channel.send("SteamAPI: GetPlayerSummaries() failed for " + message.author.name + ". Is the Steam Web API down?")
                return
        else:
            await message.channel.send(message.author.name + "님의 주소를 찾을 수 없습니다." + get_steam_id_instructions())
            if check_if_steam_url_image_can_be_posted_and_update_timestamp_if_true():
                await message.channel.send("", file=discord.File("steam.jpg"))
            return

client.run(discordBotTokenIMPORTANT)
