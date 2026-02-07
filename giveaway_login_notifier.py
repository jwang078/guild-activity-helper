import discord
import asyncio
import json
import os
import argparse
import nest_asyncio
from notifypy import Notify

# Apply nest_asyncio to allow asyncio.run() to be nested
nest_asyncio.apply()

# ASCII colors for console output
RED = "\u001b[31m"
RESET = "\u001b[0m"

class DiscordNotificationClient(discord.Client):
    """
    A discord client that listens for new messages in a specific channel
    and notifies if they match a specific prefix and username.
    """

    # The prefix to look for at the start of a message
    JOIN_LEAVE_PREFIX = "<:egg_right:1178195628615028776> "

    def __init__(self, guild_id, channel_id, igns_to_look_for, *args, **kwargs):
        # Set up intents to receive message content and guild information
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)

        self.guild_id = guild_id
        self.channel_id = channel_id
        self.igns_to_look_for = [ign.lower().strip() for ign in igns_to_look_for]

    async def on_ready(self):
        """
        This event is called when the bot successfully connects to Discord.
        """
        print(f"Logged in as {self.user}!")
        self.guild = self.get_guild(self.guild_id)
        if self.guild:
            self.channel = self.guild.get_channel(self.channel_id)
            print(f"Monitoring channel: #{self.channel.name}")
        else:
            print(f"{RED}ERROR: Guild with ID {self.guild_id} not found.{RESET}")

        print("Will look for igns", self.igns_to_look_for, "(not case sensitive)")

    async def on_message(self, message):
        """
        This event is called whenever a message is sent in a channel the bot can see.
        """
        # Ignore messages sent by the bot itself to prevent infinite loops
        # if message.author.bot:
        #     return

        # Check if the message is from the designated channel
        if message.channel.id == self.channel_id:
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                message_text = embed.description
            else:
                message_text = None
            # Check if the message content starts with the required prefix
            if message_text is not None and message_text.startswith(self.JOIN_LEAVE_PREFIX):
                print("message was a join/leave message")
                # Extract the username from the message content
                message_parts = message_text.split()
                print("message parts:", message_parts)
                # Ensure there is a word after the prefix
                if len(message_parts) > 1:
                    username_in_message = message_parts[1]
                    print("username in message", username_in_message)
                    # Check if the extracted username is in our scan list
                    if username_in_message.lower() in self.igns_to_look_for:
                        print("✅ Sending notification because username is in list")
                        notification = Notify()
                        notification.title = "GUILD GIVEAWAY"
                        notification.message = f"{username_in_message} has joined or left"
                        notification.send()


async def main(args):
    # Load sensitive configs from a JSON file (e.g., bot token, guild ID, channel ID)
    try:
        with open("data/config.json", "r") as f:
            config = json.load(f)
            BOT_TOKEN = config["BOT_TOKEN"]
            GUILD_ID = config["GUILD_ID"]
            CHANNEL_ID = config["CHANNEL_ID"]
    except FileNotFoundError:
        print(
            f"{RED}ERROR: 'data/config.json' not found. Please create this file with your credentials.{RESET}"
        )
        return

    # Create and run the Discord client
    client = DiscordNotificationClient(GUILD_ID, CHANNEL_ID, args.igns)
    await client.start(BOT_TOKEN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--igns',
        type=str,
        nargs='*',
        required=True,
        help='A list of usernames to look out for'
    )
    args = parser.parse_args()

    # Run the main async function
    try:
        asyncio.run(main(args))
    except discord.errors.LoginFailure:
        print(
            f"{RED}ERROR: Invalid bot token. Please check your token in 'data/config.json'.{RESET}"
        )
    except KeyboardInterrupt:
        print("\nExiting bot.")
