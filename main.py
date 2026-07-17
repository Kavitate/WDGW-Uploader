import asyncio
import discord
import aiohttp
import json
import os
from discord import app_commands
from discord import ButtonStyle
from discord.ui import Button, View

# Load Config
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

DISCORD_TOKEN = config["discord_token"]
WIGLE_API_TOKEN = config["wigle_api_token"]
WDGWARS_API_KEY = config["wdgwars_api_key"]

color = 0xBF00FF  # Purple

# Endpoints
WIGLE_TRANSACTIONS_URL = "https://api.wigle.net/api/v2/file/transactions?pagestart=0"
WIGLE_CSV_URL = "https://api.wigle.net/api/v2/file/csv/{transid}"
WDGWARS_UPLOAD_URL = "https://wdgwars.pl/api/upload-csv"
WDGWARS_LATEST_URL = "https://wdgwars.pl/api/upload-history?limit=1"

intents = discord.Intents.default()
intents.message_content = True

# Log File
def is_in_log(transid):
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, "r") as f:
        return transid in f.read().splitlines()

def add_to_log(transid):
    with open(LOG_FILE, "a") as f:
        f.write(f"{transid}\n")

# Bot Setup
class SyncBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("[SYNC] Slash commands synced")

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="WDGW", style=ButtonStyle.link, url="https://wdgwars.pl"))
        self.add_item(Button(label="WiGLE", style=ButtonStyle.link, url="https://wigle.net"))
        self.add_item(Button(label="Kavitate", style=ButtonStyle.link, url="https://github.com/kavitate"))

bot = SyncBot()

@bot.event
async def on_ready():
    print(f"[SYNC] Logged in as {bot.user}")
    print(f"[SYNC] Ready to sync WDGW Uploader by Kavitate")

# Embeds
def error_embed(title, description):
    return discord.Embed(title=f"{title}", description=description, color=color)

def success_embed(lines):
    description = "\n".join(f"{name} {value}" for name, value in lines)
    return discord.Embed(title="✅ Upload Successful!", description=description, color=color)

def info_embed(title, description):
    return discord.Embed(title=f"{title}", description=description, color=color)

# WDGW API
async def get_wdgwars_latest(session):
    headers = {"X-API-Key": WDGWARS_API_KEY, "User-Agent": "wigle-wdgwars-discord-bot/1.0"}
    try:
        async with session.get(WDGWARS_LATEST_URL, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                uploads = data.get("uploads", [])
                if uploads:
                    return uploads[0]
    except Exception as e:
        print(f"[SYNC] Warning: couldn't fetch WDGW latest: {e}")
    return None

def build_stats_lines(transid, wdgw_entry):
    result = wdgw_entry["result"]
    wdgw_filename = wdgw_entry.get("filename", "unknown")
    imported = result.get("imported", 0)
    captured = result.get("captured", 0)
    updated = result.get("updated", 0)
    aircraft_imported = result.get("aircraft_imported", 0)
    duplicates = result.get("duplicates", 0)
    total_received = imported + captured + updated + aircraft_imported + duplicates

    return [
        ("🔑 **Transaction ID:**", f"`{transid}`"),
        ("📄 **File Name:**", f"`{wdgw_filename}`"),
        ("📊 **Total Received:**", str(total_received)),
        ("🆕 **New:**", str(imported)),
        ("🎯 **Captured:**", str(captured)),
        ("🔄 **Reinforced:**", str(updated)),
        ("✈️ **Aircraft Imported:**", str(aircraft_imported)),
        ("♻️ **Duplicates:**", str(duplicates)),
    ]

@bot.tree.command(name="sync", description="Pulls the latest WiGLE upload and pushes it to WDGW.")
async def sync_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Fetch latest WiGLE transaction
            wigle_headers = {"Authorization": f"Basic {WIGLE_API_TOKEN}", "User-Agent": "wigle-wdgwars-discord-bot/1.0"}

            async with session.get(WIGLE_TRANSACTIONS_URL, headers=wigle_headers) as resp:
                if resp.status == 204:
                    await interaction.followup.send(
                        embed=info_embed("⌛ Still Processing",
                            "Latest file hasn't finished uploading to WiGLE.\nPlease try again later."))
                    return

                if resp.status != 200:
                    body = await resp.text()
                    await interaction.followup.send(
                        embed=error_embed("🚫 Upload Failed!",
                            f"WiGLE transactions API returned HTTP {resp.status}.\n```{body[:200]}```"))
                    return

                data = await resp.json()

            results = data.get("results", [])
            if not results:
                await interaction.followup.send(
                    embed=error_embed("🚫 Upload Failed!", "No uploads found on your WiGLE account."))
                return

            latest = results[0]
            transid = latest.get("transid")
            filename = latest.get("fileName", "unknown")
            wait = latest.get("wait")

            if not transid:
                await interaction.followup.send(
                    embed=error_embed("🚫 Upload Failed!", "Couldn't find a transaction ID in the WiGLE response."))
                return

            # Step 2: Check if WiGLE is still processing
            if wait:
                await interaction.followup.send(
                    embed=info_embed("⌛ Still Processing!",
                        f"Latest file hasn't finished uploading to WiGLE.\n"
                        f"Queue Position: `{wait}`\n"
                        f"Transaction ID: `{transid}`\n"
                        f"File Name: `{filename}`\n\n"
                        f"Please try again later."))
                return

            # Step 3: Check log for duplicate
            if is_in_log(transid):
                await interaction.followup.send(
                    embed=info_embed("📄 Duplicate File",
                        f"\nWiGLE transaction ID `{transid}` has already been uploaded to WDGW.\n"
                        f"File Name: `{filename}`"))
                return

            # Step 4: Log the transaction ID
            add_to_log(transid)

            print(f"[SYNC] Syncing WiGLE upload: {transid} ({filename})")

            # Step 5: Download CSV from WiGLE
            csv_url = WIGLE_CSV_URL.format(transid=transid)

            async with session.get(csv_url, headers=wigle_headers) as resp:
                if resp.status == 204:
                    await interaction.followup.send(
                        embed=info_embed("⌛ Still Processing!",
                            f"Latest file hasn't finished uploading to WiGLE.\n"
                            f"Transaction ID: `{transid}`\n"
                            f"File Name: `{filename}`\n\n"
                            f"Please try again later."))
                    return

                if resp.status != 200:
                    body = await resp.text()
                    await interaction.followup.send(
                        embed=error_embed("🚫 Upload Failed!",
                            f"WiGLE CSV download returned HTTP {resp.status}.\n```{body[:200]}```"))
                    return

                csv_data = await resp.read()

            if not csv_data:
                await interaction.followup.send(
                    embed=error_embed("🚫 Upload Failed!", "WiGLE returned an empty CSV file."))
                return

            csv_size_kb = len(csv_data) / 1024
            print(f"[SYNC] Downloaded CSV: {csv_size_kb:.1f} KB")

            # Step 6: Upload CSV to WDGW
            wdgwars_headers = {"X-API-Key": WDGWARS_API_KEY, "User-Agent": "wigle-wdgwars-discord-bot/1.0"}

            form = aiohttp.FormData()
            form.add_field("file", csv_data, filename=f"{transid}.csv", content_type="text/csv")

            async with session.post(WDGWARS_UPLOAD_URL, headers=wdgwars_headers, data=form) as resp:
                response_text = await resp.text()

                if resp.status in (200, 202):
                    # Step 7: Poll WDGW for stats (up to 30s)
                    expected_filename = f"{transid}.csv"
                    wdgw_result = None
                    max_attempts = 6
                    for attempt in range(max_attempts):
                        if attempt > 0:
                            await asyncio.sleep(5)
                        wdgw_latest = await get_wdgwars_latest(session)
                        if wdgw_latest and wdgw_latest.get("filename") == expected_filename and wdgw_latest.get("result"):
                            wdgw_result = wdgw_latest
                            break
                        print(f"[SYNC] Waiting for WDGW to process... (attempt {attempt + 1}/{max_attempts})")

                    if wdgw_result:
                        lines = build_stats_lines(transid, wdgw_result)
                        await interaction.followup.send(embed=success_embed(lines))
                    else:
                        await interaction.followup.send(embed=info_embed(
                            "⌛ Uploaded — Awaiting Results",
                            f"File `{transid}.csv` was uploaded to WDGW but is still being processed.\n"
                            f"Run `/sync` again in a minute to see your stats."))

                    print(f"[SYNC] Upload Successful!: {transid}")
                else:
                    await interaction.followup.send(
                        embed=error_embed("🚫 Upload Failed!",
                            f"WDGW returned HTTP {resp.status}.\n```{response_text[:300]}```"))
                    print(f"[SYNC] Upload failed!: HTTP {resp.status}")

    except aiohttp.ClientError as e:
        await interaction.followup.send(
            embed=error_embed("🚫 Upload Failed!", f"Network error: `{e}`"))
        print(f"[SYNC] Network error: {e}")
    except Exception as e:
        await interaction.followup.send(
            embed=error_embed("🚫 Upload Failed!", f"Unexpected error: `{e}`"))
        print(f"[SYNC] Error: {e}")

@bot.tree.command(name="help", description="Displays help information for WDGW Uploader.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    help_text = (
        "**Command List**\n"
        "`/sync` - Pulls the latest WiGLE upload and pushes it to WDGW.\n\n"
        "- Allow time for processing after an initial WiGLE upload.\n"
        "- The bot will only pull the most recent upload to WiGLE.\n\n")

    embed = discord.Embed(title="WDGW Uploader Information", description=help_text, color=color)
    embed.set_footer(text="WDGW Uploader by Kavitate")
    embed.set_image(url="https://i.imgur.com/XpcN6uA.png")

    view = HelpView()
    await interaction.followup.send(embed=embed, view=view)

if __name__ == "__main__":
    if DISCORD_TOKEN == "discord_token":
        print("ERROR: Update config.json with your actual tokens!")
        exit(1)

    bot.run(DISCORD_TOKEN)
