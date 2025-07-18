import discord
import asyncio
import json
import nest_asyncio
import argparse

nest_asyncio.apply()

class DiscordRoleUpdaterClient(discord.Client):
    """
    A discord client that updates member roles based on an external guild list file.
    """

    ROLE_NAME = "active coolio"  # The role to be added or removed

    def __init__(self, guild_id, member_names, active_list, *args, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(intents=intents, *args, **kwargs)

        self.guild_id = guild_id
        self.member_names = member_names
        self.active_list = active_list

    async def on_ready(self):
        print(f"Logged in as {self.user}")

        print("Getting guild...")
        guild = self.get_guild(self.guild_id)
        if guild is None:
            print("Guild not found.")
            await self.close()
            return

        print(f"Getting role {self.ROLE_NAME}...")
        role = discord.utils.get(guild.roles, name=self.ROLE_NAME)
        if role is None:
            print(f"Role '{self.ROLE_NAME}' not found in guild.")
            await self.close()
            return

        print("Fetching members...")
        # Fetch members to ensure full member list
        await guild.chunk()

        print(f"Found {len(guild.members)} members in the guild.")
        for name in self.member_names:
            # Search by nickname, name, and global_name
            member = discord.utils.find(
                lambda m:
                    (m.nick is not None and m.nick.strip().lower() == name.strip().lower()) \
                    or (m.name is not None and m.name.strip().lower() == name.strip().lower()) \
                    or (m.global_name is not None and m.global_name.strip().lower() == name.strip().lower()),
                guild.members
            )

            if member is None:
                print(f"{name} not found in server (by nickname or username).")
                continue

            # For demonstration, let's treat everyone in the list as requiring the 'active coolio' role
            # Adjust logic as needed for your specific promotion/demotion rules

            if name in self.active_list:
                if role not in member.roles:
                    await member.add_roles(role)
                    print(f"✅ Added role '{self.ROLE_NAME}' to {name}.")
                else:
                    print(f"{name} already has role '{self.ROLE_NAME}'.")
            else:
                if role in member.roles:
                    await member.remove_roles(role)
                    print(f"❌ Removed role '{self.ROLE_NAME}' from {name}.")
                else:
                    print(f"{name} does not have role '{self.ROLE_NAME}' to remove.")

        await self.close()

def load_guild_list(filename="data/guild_list.txt"):
    """
    Parses data/guild_list.txt in the same style as ActivityTracker.load_guild_list()
    Returns a flattened list of all IGNs across all ranks.
    """
    guild_list = {}
    with open(filename, "r") as f:
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

    # Flatten to single list of member names
    all_members = [ign.strip() for igns in guild_list.values() for ign in igns]
    return all_members

def load_active_list(filename="output/active_igns.txt"):
    """
    Loads the active list of members from a file.
    Returns a list of member names.
    """
    try:
        with open(filename, "r") as f:
            active_list = [line.strip() for line in f if line.strip()]
        return active_list
    except FileNotFoundError:
        print(f"File {filename} not found. Returning empty active list.")
        return []

async def main(args):
    # Load config
    with open("data/config.json", "r") as f:
        config = json.load(f)
        BOT_TOKEN = config["BOT_TOKEN"]
        GUILD_ID = config["GUILD_ID"]

    member_names = load_guild_list()
    active_list = load_active_list()

    client = DiscordRoleUpdaterClient(GUILD_ID, member_names, active_list)
    await client.start(BOT_TOKEN)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    asyncio.run(main(args))
