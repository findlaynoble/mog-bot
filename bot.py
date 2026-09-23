import os
import discord
from discord import app_commands
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("MOG_API_KEY")

API_BASE = "https://mogalts.win/v1"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

class MogBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

client = MogBot()

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.tree.command(name="stock", description="Check current stock counts and prices")
async def stock(interaction: discord.Interaction):
    response = requests.get(f"{API_BASE}/stock", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        embed = discord.Embed(title="Mog Alts Stock", color=discord.Color.blue())
        embed.description = f"```json\n{data}\n```"
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Failed to fetch stock. Error: {response.text}", ephemeral=True)

@client.tree.command(name="buy", description="Purchase accounts")
@app_commands.describe(category="The category of accounts", amount="Quantity to buy")
async def buy(interaction: discord.Interaction, category: str, amount: int):
    await interaction.response.defer(thinking=True)
    payload = {"category": category, "amount": amount}
    response = requests.post(f"{API_BASE}/buy", json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        try:
            await interaction.user.send(f"**Purchase Successful!**\n```json\n{response.text}\n```")
            await interaction.followup.send("✅ Purchase successful! Check your Direct Messages for the details.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Purchased successfully, but I couldn't DM you! Please open your DMs.", ephemeral=True)
    else:
        await interaction.followup.send(f"Purchase failed: {response.text}", ephemeral=True)

@client.tree.command(name="balance", description="Check remaining credit balance")
async def balance(interaction: discord.Interaction):
    response = requests.get(f"{API_BASE}/balance", headers=HEADERS)
    if response.status_code == 200:
        await interaction.response.send_message(f"Wallet Balance Info:\n```json\n{response.text}\n```", ephemeral=True)
    else:
        await interaction.response.send_message(f"Failed to fetch balance: {response.text}", ephemeral=True)

@client.tree.command(name="replace", description="Request an account replacement using Order ID")
@app_commands.describe(order_id="The Order ID to replace")
async def replace(interaction: discord.Interaction, order_id: str):
    response = requests.post(f"{API_BASE}/replace/{order_id}", headers=HEADERS)
    if response.status_code == 200:
        await interaction.response.send_message(f"Replacement requested successfully:\n```json\n{response.text}```", ephemeral=True)
    else:
        await interaction.response.send_message(f"Replacement failed: {response.text}", ephemeral=True)

client.run(TOKEN)