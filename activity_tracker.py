import discord
import asyncio
import json
import os
import datetime
import pytz
import traceback
import argparse


# for running main() as an async function
import nest_asyncio
nest_asyncio.apply()

# ASCII colors
RED = "\u001B[31m"
RESET = "\u001B[0m"

class DiscordLogClient(discord.Client):
    """
    A discord client that logs join/leave messages from a specific channel in a specific guild.
    Specific syntax used for join/leave messages
    """

    JOIN_LEAVE_PREFIX = "<:egg_right:1178195628615028776> "
    JOIN_COLOR = discord.colour.Colour(4714569)
    LEAVE_COLOR = discord.colour.Colour(15747399)

    # Saves join/leave logs from discord to a file in order of timestamp

    def __init__(self, guild_id, channel_id, max_messages, max_days, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)

        self.guild_id = guild_id
        self.channel_id = channel_id
        self.max_messages = max_messages
        self.max_days = max_days

        self.last_log_filename = None

    async def on_ready(self):
        """
        When the client is run, it downloads and saves logs, then quits.
        """
        print(f'Logged in as {self.user}')
        self.guild = self.get_guild(self.guild_id)
        self.channel = self.guild.get_channel(self.channel_id)

        await self.save_messages()
        await self.close()

    def get_last_log_filename(self):
        return self.last_log_filename

    def get_log_name(self):
        my_time = datetime.datetime.now().strftime("%Y-%m-%d.%f")
        return f"logs/{my_time}-logs-guild{self.guild_id}-channel{self.channel_id}"

    def save_to_file(self, logs):
        """
        Save logs to a file
        """
        filename = f"{self.get_log_name()}.json"
        print("Will save logs to ", filename)
        self.last_log_filename = filename
        # save messages as a json file
        print(f"Saving logs to {filename}")
        with open(filename, 'w') as f:
            json.dump(logs, f)

    async def save_messages(self):
        """
        Download logs from discord and save them to a file
        """

        logs = []
        i = 0
        today = None
        
        try:
            async for m in self.channel.history(limit=self.max_messages):
                # Parse out the join/leave messages
                if len(m.embeds) > 0:
                    embed = m.embeds[0]
                    msg = embed.description
                    timestamp = m.created_at
                    if today is None:
                        today = datetime.datetime.now(timestamp.tzinfo)
                        max_day = today - datetime.timedelta(days=self.max_days + 1) # + 1 for some leeway

                    if msg is None:
                        # prob quickdesh went offline
                        continue
                    if msg.startswith(self.JOIN_LEAVE_PREFIX):
                        # example log:
                        # '<:egg_right:1178195628615028776> MyIGN has gone into a deep slumber!'
                        timestamp_str = str(timestamp) # str of a datetime object
                        ign = msg[len(self.JOIN_LEAVE_PREFIX):].split(" ")[0]
                        if embed.color == self.JOIN_COLOR:
                            is_join = True
                        elif embed.color == self.LEAVE_COLOR:
                            is_join = False
                        else:
                            print(f"{RED}WARNING: Unknown join/leave color {embed.color} for embed for message {msg}. Skipping.{RESET}")
                            continue

                        logs.insert(0,{'timestamp': timestamp_str, 'ign': ign, "is_join": is_join, "is_guild_join": False})
                    elif "joined the guild" in msg:
                        timestamp_str = str(timestamp) # str of a datetime object
                        ign = msg.split(" ")[0]
                        logs.insert(0,{'timestamp': timestamp_str, 'ign': ign, "is_join": True, "is_guild_join": True})
                    if timestamp < max_day:
                        break

                i += 1
                if i % 100 == 0:
                    print(f"msg# {i}/{self.max_messages}, day# {(today - timestamp).days}/{self.max_days}")
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            print("Error saving messages. Saving intermediate logs and exiting")

            self.save_to_file(logs)
            return
        
        # TODO possibly sort the logs by timestamp if they're not already sorted
        self.save_to_file(logs)
        return
 
class ActivityTracker():
    """
    Given the saved logs from DiscordLogClient, calculate the activity of each user in the guild.
    Assumes the logs are sorted with the least recent message first
    """

    # Key names for the activity dictionary
    LAST_JOIN_KEY = 'last_join'
    LAST_LEAVE_KEY = 'last_leave'
    LAST_LONG_JOIN_KEY = 'last_long_join'

    # Defining what a join means
    MINS_FOR_LONG_JOIN = 30
    MINS_FOR_RECONNECT_TIMEOUT = 60*2
    MINS_FOR_JOIN_LOG_TIMEOUT = 60*24

    # Search for 2 joins within the last 60 days
    MINS_FOR_ACTIVITY_RANGE = 60*24*60 # search within 60 days
    NUM_LONG_JOINS_FOR_ACTIVITY = 2 # search for 2 long joins within the activity range

    # Print config
    IGN_WIDTH = 20  # Adjust the width as needed
    LAST_JOIN_WIDTH = 15
    # last long join width is variable
    PRINT_TIMEZONE = pytz.timezone('US/Eastern')

    # Raw promotion criteria
    MINS_FOR_RAW_PROMOTION_ACTIVITY_RANGE = 60*24*7 # within the last week
    NUM_LONG_JOINS_FOR_RAW_PROMOTION = 1
    MINS_FOR_RAW_JOIN_DATE_PROMOTION_RANGE = 60*24*30 # join for a month

    # Boiled promotion criteria
    MINS_FOR_BOILED_PROMOTION_ACTIVITY_RANGE = 60*24*7 # within the last week
    NUM_LONG_JOINS_FOR_BOILED_PROMOTION = 1
    MINS_FOR_BOILED_JOIN_DATE_PROMOTION_RANGE = 60*24*91 # join for 3 months aka approx 91 days
    SCRAMBLED_SB_LEVEL = 240

    # File names for additional logs
    GUILD_LIST_FILENAME = "data/guild_list.txt"
    SB_LEVEL_LIST_FILENAME = "data/sb_level_list.txt"

    def __init__(self):
        self._reset()

    def _reset(self):
        self.activity = {} # key: ign, value: {'last_join': timestamp, 'last_leave': timestamp, 'last_long_joins': [date1, date2, ...]}

    def get_ign(self, log):
        return log['ign']
    
    def get_is_join(self, log):
        return log['is_join']
    
    def get_is_guild_join(self, log):
        return log['is_guild_join']
    
    def get_timestamp(self, log):
        return datetime.datetime.fromisoformat(log['timestamp'])
    
    def is_long_join(self, start, end):
        return self.is_time_within_mins(start, end, self.MINS_FOR_LONG_JOIN)
    
    def is_time_within_mins(self, start, end, mins):
        diff = end - start
        return diff.seconds < 60*mins
    
    def load_guild_list(self):
        """
        Load igns from the list in self.GUILD_LIST_FILENAME
        """
        # TODO make this load automagically from the discord bot, not from a text file
        # ^ actually, that's hard because that requires calling another bot
        guild_list = {}
        with open(self.GUILD_LIST_FILENAME, "r") as f:
            # Skip the header
            line = next(f)
            while not line.startswith("--"):
                line = next(f)
            current_rank = line.strip()[3:-3]

            # Parse the file
            for line in f:
                if line.startswith("--"):
                    current_rank = line.strip()[3:-3]
                elif "●" in line:
                    igns = line.split("●")
                    guild_list[current_rank] = [ign.strip() for ign in igns if ign.strip() != ""]
                else:
                    # Reached the end
                    break
        return guild_list

    def print_by_guild_rank(self, ign_dict, title):
        print("="*69)
        print(title)
        for rank, igns in ign_dict.items():
            if len(igns) > 0:
                print()
                print(rank)
                print("-", ", ".join(igns))
        print("\n")

    def get_igns_by_rank(self, igns):
        igns_by_rank = {}
        for rank in self.guild_list_dict.keys():
            rank_igns = [ign for ign in igns if ign in self.guild_list_dict[rank]]
            igns_by_rank[rank] = rank_igns
        return igns_by_rank
    
    def load_sb_level_list(self):
        """
        Load sb levels from the list in SB_LEVEL_LIST_FILENAME
        """
        sb_levels = {}
        with open(self.SB_LEVEL_LIST_FILENAME, "r") as f:
            for line in f:
                if ":" in line:
                    ign, sb_level = line.split(":")[:2]
                    ign = ign.strip().split(" ")[1]
                    sb_level = sb_level.strip().split(" ")[0]
                    sb_levels[ign] = float(sb_level)
        return sb_levels
    
    def get_raw_to_boiled_promotion_igns(self):
        """
        Get igns that should be promoted from raw to boiled
        """

        raw_igns = self.guild_list_dict["Raw Egg"]
        today = datetime.datetime.now().astimezone(self.PRINT_TIMEZONE)

        activity_range_start = self.nearest_log_time - datetime.timedelta(minutes=self.MINS_FOR_RAW_PROMOTION_ACTIVITY_RANGE)
        join_date_end = today - datetime.timedelta(minutes=self.MINS_FOR_RAW_JOIN_DATE_PROMOTION_RANGE)

        # Is active overall, had a long join in the last week, and joined the guild at least a month ago
        raw_promotion_igns = [
            ign for ign in raw_igns \
                if ign in self.active_igns \
                    and sum([t < activity_range_start for t in self.activity[ign][self.LAST_LONG_JOIN_KEY][-self.NUM_LONG_JOINS_FOR_RAW_PROMOTION:]]) == 0 \
                    and (ign not in self.known_guild_join_dates or self.known_guild_join_dates[ign] <= join_date_end)
        ]

        return raw_promotion_igns
    
    def get_boiled_to_scrambled_promotion_igns(self):
        """
        Get igns that should be promoted from boiled to scrambled
        """
        boiled_igns = self.guild_list_dict["Hard Boiled Egg"]
        today = datetime.datetime.now().astimezone(self.PRINT_TIMEZONE)

        activity_range_start = self.nearest_log_time - datetime.timedelta(minutes=self.MINS_FOR_BOILED_PROMOTION_ACTIVITY_RANGE)
        join_date_end = today - datetime.timedelta(minutes=self.MINS_FOR_BOILED_JOIN_DATE_PROMOTION_RANGE)

        # Is active overall, had a long join in the last week, joined the guild at least 3 months ago, and sb level 240
        boiled_promotion_igns = [
            ign for ign in boiled_igns \
                if ign in self.active_igns \
                    and sum([t < activity_range_start for t in self.activity[ign][self.LAST_LONG_JOIN_KEY][-self.NUM_LONG_JOINS_FOR_BOILED_PROMOTION:]]) == 0 \
                    and (ign not in self.known_guild_join_dates or self.known_guild_join_dates[ign] <= join_date_end) \
                    and self.sb_level_dict.get(ign, -1) >= self.SCRAMBLED_SB_LEVEL
        ]
        
        return boiled_promotion_igns

    def calculate_activity(self, log_file):
        """
        Calculate whether a person is currently active using the defined constants
        """
        with open(log_file, 'r') as f:
            logs = json.load(f)

        self.guild_list_dict = self.load_guild_list()
        self.print_by_guild_rank(self.guild_list_dict, "Guild list:")

        self.sb_level_dict = self.load_sb_level_list()

        guild_list = [ign for igns in self.guild_list_dict.values() for ign in igns]

        self.furthest_log_time = self.get_timestamp(logs[0])
        self.nearest_log_time = self.get_timestamp(logs[-1])

        self.known_guild_join_dates = {} # key: ign, value: timestamp

        activity_grace_period_end = self.furthest_log_time - datetime.timedelta(minutes=self.MINS_FOR_ACTIVITY_RANGE)
        igns_in_grace_period = set()

        # Parse logs
        for log in logs:
            ign = self.get_ign(log)
            if ign not in self.activity:
                self.activity[ign] = {self.LAST_JOIN_KEY: None, self.LAST_LEAVE_KEY: None, self.LAST_LONG_JOIN_KEY: []}

            # Parse this log
            is_join = self.get_is_join(log)
            is_guild_join = self.get_is_guild_join(log)
            timestamp = self.get_timestamp(log)
            
            if is_join:
                # no recorded last join, or they just reconnected, or it's been a long while since the last recorded join
                if self.activity[ign][self.LAST_LEAVE_KEY] is None \
                        or not self.is_time_within_mins(self.activity[ign][self.LAST_LEAVE_KEY], timestamp, self.MINS_FOR_RECONNECT_TIMEOUT) \
                        or self.is_time_within_mins(self.activity[ign][self.LAST_JOIN_KEY], timestamp, self.MINS_FOR_JOIN_LOG_TIMEOUT):
                    self.activity[ign][self.LAST_JOIN_KEY] = timestamp
                
                if is_guild_join:
                    self.known_guild_join_dates[ign] = timestamp
                    if timestamp >= activity_grace_period_end:
                        igns_in_grace_period.add(ign)
            else:
                self.activity[ign][self.LAST_LEAVE_KEY] = timestamp

                last_join_timestamp = self.activity[ign][self.LAST_JOIN_KEY]
                if last_join_timestamp is None:
                    self.activity[ign][self.LAST_JOIN_KEY] = self.furthest_log_time
                    last_join_timestamp = self.furthest_log_time
                
                if not self.is_time_within_mins(last_join_timestamp, timestamp, self.MINS_FOR_LONG_JOIN):
                    if len(self.activity[ign][self.LAST_LONG_JOIN_KEY]) == 0 \
                            or self.activity[ign][self.LAST_LONG_JOIN_KEY][-1] != self.activity[ign][self.LAST_JOIN_KEY]:
                        self.activity[ign][self.LAST_LONG_JOIN_KEY].append(self.activity[ign][self.LAST_JOIN_KEY])
        
        # Sort igns in each category by last join time
        self.active_igns = sorted(self.get_active_igns(), key=lambda ign: self.activity[ign][self.LAST_JOIN_KEY], reverse=True)
        self.inactive_igns = sorted(
                                [ign for ign in self.activity.keys() if ign not in self.active_igns], \
                                key=lambda ign: self.activity[ign][self.LAST_JOIN_KEY], reverse=True
        ) + sorted([ign for ign in guild_list if ign not in self.activity.keys()])
        self.grace_period_igns = sorted(igns_in_grace_period, key=lambda ign: self.activity[ign][self.LAST_JOIN_KEY], reverse=True)

        # Remove igns that aren't currently in the guild
        self.active_igns = [ign for ign in self.active_igns if ign in guild_list]
        self.inactive_igns = [ign for ign in self.inactive_igns if ign in guild_list]
        self.grace_period_igns = [ign for ign in self.grace_period_igns if ign in guild_list]

        # Remove grace period igns from the inactive list, and remove active igns from the grace period list
        self.grace_period_igns = [ign for ign in self.grace_period_igns if ign not in self.active_igns]
        self.inactive_igns = [ign for ign in self.inactive_igns if ign not in self.grace_period_igns]

        # Get promotion lists
        self.raw_to_boiled_promotion_igns = self.get_raw_to_boiled_promotion_igns()
        self.boiled_to_scrambled_promotion_igns = self.get_boiled_to_scrambled_promotion_igns()

        # Print results    
        self.print_activity_log()

        # Printing disclaimers
        furthest_log_time_str = self.furthest_log_time.astimezone(self.PRINT_TIMEZONE).strftime('%b %d %Y %H:%M')
        nearest_log_time_str = self.nearest_log_time.astimezone(self.PRINT_TIMEZONE).strftime('%b %d %Y %H:%M')
        # Get the last modification time
        guild_list_last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.GUILD_LIST_FILENAME)).astimezone(self.PRINT_TIMEZONE)
        sb_level_list_last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.SB_LEVEL_LIST_FILENAME)).astimezone(self.PRINT_TIMEZONE)
        sb_level_list_last_modified_str = sb_level_list_last_modified.strftime('%b %d %Y %H:%M')
        guild_list_last_modified_str = guild_list_last_modified.strftime('%b %d %Y %H:%M')
        today = datetime.datetime.now().astimezone(self.PRINT_TIMEZONE)
        print(f"\nActivity calculation using logs from [{furthest_log_time_str}] to [{nearest_log_time_str}]" \
                + f" ({(self.nearest_log_time - self.furthest_log_time).days} days)")
        print(f"Guild list last updated: {guild_list_last_modified_str}")
        if (today - guild_list_last_modified).days > 1:
            print(f"{RED}WARNING: Guild list has not been updated in the last day. Check for updates.{RESET}")
        print(f"SB level list last updated: {sb_level_list_last_modified_str}")
        if (today - sb_level_list_last_modified).days > 1:
            print(f"{RED}WARNING: SB level list has not been updated in the last day. Check for updates.{RESET}")
        print("Note: This does not support ign changes")
        print()

    def print_activity_log(self):
        """
        Print results of activity calculation
        """
        def print_header():
            ign_str = f"{'IGN':<{self.IGN_WIDTH}}"
            last_join_str = f"{'Last Join':<{self.LAST_JOIN_WIDTH}}"
            last_long_joins_str = "Last Long Joins(s)"
            print(f"{ign_str}\t{last_join_str}\t{last_long_joins_str}")
            print("-"*69)

        def print_row(ign, info):
            ign_str = f"{ign:<{self.IGN_WIDTH}}"
            if info is not None:
                last_join_str = f"{info[self.LAST_JOIN_KEY].astimezone(self.PRINT_TIMEZONE).strftime('%b %d %H:%M'):<{self.LAST_JOIN_WIDTH}}"
                last_long_joins_str = f"{[t.astimezone(self.PRINT_TIMEZONE).strftime('%b %d %H:%M') for t in info[self.LAST_LONG_JOIN_KEY][:-self.NUM_LONG_JOINS_FOR_ACTIVITY-1:-1]]}"
                if len(info[self.LAST_LONG_JOIN_KEY]) > self.NUM_LONG_JOINS_FOR_ACTIVITY:
                    last_long_joins_str = last_long_joins_str[:-1] + ", ...]"
            else:
                last_join_str = f"{'N/A':<{self.LAST_JOIN_WIDTH}}"
                last_long_joins_str = "[]"
            print(f"{ign_str}\t{last_join_str}\t{last_long_joins_str}")

        # Get activity per ign
        active_activity = {ign: self.activity[ign] for ign in self.active_igns}
        grace_period_activity = {ign: self.activity[ign] for ign in self.grace_period_igns}
        inactive_activity = {ign: self.activity[ign] if ign in self.activity else None for ign in self.inactive_igns}

        # Print active players
        active_ign_dict = self.get_igns_by_rank(self.active_igns)
        self.print_by_guild_rank(active_ign_dict, "Active list:")
        print_header()
        for ign, info in active_activity.items():
            print_row(ign, info)

        print("\n\n")

        # Print players not currently active but are in grace period
        grace_period_ign_dict = self.get_igns_by_rank(self.grace_period_igns)
        self.print_by_guild_rank(grace_period_ign_dict, "Grace period list (currently inactive):")
        print_header()
        for ign, info in grace_period_activity.items():
            print_row(ign, info)

        print("\n\n")

        # Print inactive players
        inactive_ign_dict = self.get_igns_by_rank(self.inactive_igns)
        self.print_by_guild_rank(inactive_ign_dict, "Inactive list:")
        print_header()
        for ign, info in inactive_activity.items():
            print_row(ign, info)

        print("\n\n")

        # Print raw promotion list
        print("Raw to Boiled promotion list:")
        # print guild join date possible ambiguity warning
        unknown_join_igns = [ign for ign in self.raw_to_boiled_promotion_igns if ign not in self.known_guild_join_dates]
        if len(unknown_join_igns) > 0:
            print(f"{RED}WARNING: No recent guild join date logs for {unknown_join_igns}. Manually check guild join date before promoting{RESET}")
        print([ign for ign in self.raw_to_boiled_promotion_igns if ign not in unknown_join_igns])

        print()

        # Print boiled promotion list
        print("Boiled to Scrambled promotion list:")
        # print guild join date possible ambiguity warning
        unknown_join_igns = [ign for ign in self.boiled_to_scrambled_promotion_igns if ign not in self.known_guild_join_dates]
        if len(unknown_join_igns) > 0:
            print(f"{RED}WARNING: No recent guild join date logs for {unknown_join_igns}. Manually check guild join date before promoting{RESET}")
        print([ign for ign in self.boiled_to_scrambled_promotion_igns if ign not in unknown_join_igns])

    def get_active_igns(self):
        """
        Use requirements for activity
        """
        return [ign for ign in self.activity.keys() \
                    if len(self.activity[ign][self.LAST_LONG_JOIN_KEY]) >= self.NUM_LONG_JOINS_FOR_ACTIVITY]
         
async def main(args):
    # Load sensitive configs like guild ID, channel ID, and bot token
    with open("data/config.json", "r") as f:
        config = json.load(f)
        # From https://discord.com/developers/applications . Click on bot name, then go to Bot tab, then get token
        BOT_TOKEN = config["BOT_TOKEN"]
        # From discord, right click on the guild, then copy ID
        GUILD_ID = config["GUILD_ID"]
        # From discord, right click on the channel, then copy ID
        CHANNEL_ID = config["CHANNEL_ID"]

    # Get join/leave logs
    log_file = None
    if args.log_file is None:
        # Download logs from discord
        client = DiscordLogClient(GUILD_ID, CHANNEL_ID, max_messages=args.max_messages, max_days=args.max_days)
        client.run(BOT_TOKEN)
        log_file = client.get_last_log_filename()
    else:
        log_file = args.log_file

    # Calculate activity and print
    tracker = ActivityTracker()
    tracker.calculate_activity(log_file)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_messages', '-n', type=int, default=300_000,
                        help='Max number of messages to save')
    parser.add_argument('--max_days', '-d', type=int, default=60,
                        help='Max number of days of messages to save')
    parser.add_argument('--log_file', '-f', required=False, type=str, default=None,
                        help="Set this json file path to use offline data and don't download")
    args = parser.parse_args()
    asyncio.run(main(args))
