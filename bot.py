import os
import asyncio
import discord
from discord import app_commands
from discord.ui import Button, View, Select
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

# --- Quantity Selection View ---
class QuantitySelectView(View):
    def __init__(self, category_name: str):
        super().__init__(timeout=60)
        self.category_name = category_name

    @discord.ui.select(
        placeholder="Select quantity...",
        options=[
            discord.SelectOption(label="1", value="1"),
            discord.SelectOption(label="2", value="2"),
            discord.SelectOption(label="3", value="3"),
            discord.SelectOption(label="5", value="5"),
            discord.SelectOption(label="10", value="10"),
        ]
    )
    async def select_quantity(self, interaction: discord.Interaction, select: Select):
        amount = int(select.values[0])
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        payload = {"category": self.category_name, "amount": amount}
        
        try:
            response = await asyncio.to_thread(
                requests.post, f"{API_BASE}/buy", json=payload, headers=HEADERS, timeout=30
            )
            
            if response.status_code == 200:
                data = response.text
                
                # Send confirmation header first
                await interaction.followup.send(f"✅ **Purchase Successful ({self.category_name} x{amount})!** Here are your session tokens:", ephemeral=True)
                
                # Split tokens into chunks of 1900 characters if too long for Discord's message limit
                chunks = [data[i:i+1900] for i in range(0, len(data), 1900)]
                for chunk in chunks:
                    await interaction.followup.send(f"```json\n{chunk}\n```", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Purchase failed: {response.text}", ephemeral=True)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ The purchase request timed out after 30 seconds.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An unexpected error occurred: {str(e)}", ephemeral=True)

# --- Category Selection Dropdown ---
class CategorySelect(Select):
    def __init__(self, categories):
        options = []
        for cat in categories:
            name = cat.get("name")
            count = cat.get("count")
            price = cat.get("price")
            if count > 0:
                options.append(discord.SelectOption(
                    label=name, 
                    description=f"Stock: {count} | Price: ${price}", 
                    value=name
                ))
        
        if not options:
            options.append(discord.SelectOption(label="No Stock Available", value="none"))

        super().__init__(placeholder="Choose an account category to buy...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ There is no stock available right now.", ephemeral=True)
            return
            
        chosen_category = self.values[0]
        view = QuantitySelectView(chosen_category)
        await interaction.response.send_message(f"You selected **{chosen_category}**. Now select how many you want to buy:", view=view, ephemeral=True)

class BuyDropdownView(View):
    def __init__(self, categories):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories))

# --- Main Control Panel View ---
class MogControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📊 Check Stock", style=discord.ButtonStyle.primary, custom_id="btn_stock")
    async def stock_button(self, interaction: discord.Interaction, button: Button):
        try:
            response = await asyncio.to_thread(
                requests.get, f"{API_BASE}/stock", headers=HEADERS, timeout=10
            )
        except Exception:
            await interaction.response.send_message("❌ Stock request timed out.", ephemeral=True)
            return

        if response.status_code == 200:
            data = response.json()
            categories = data.get("data", {}).get("categories", [])
            
            embed = discord.Embed(title="📦 Mog Alts Live Stock", color=discord.Color.blue())
            for cat in categories:
                embed.add_field(
                    name=cat.get("name"),
                    value=f"Stock: **{cat.get('count')}**\nPrice: **${cat.get('price')}**\nUnset Names: {cat.get('nonameset')}",
                    inline=True
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to fetch stock. Error: {response.text}", ephemeral=True)

    @discord.ui.button(label="💰 Balance", style=discord.ButtonStyle.secondary, custom_id="btn_balance")
    async def balance_button(self, interaction: discord.Interaction, button: Button):
        try:
            response = await asyncio.to_thread(
                requests.get, f"{API_BASE}/balance", headers=HEADERS, timeout=10
            )
        except Exception:
            await interaction.response.send_message("❌ Balance request timed out.", ephemeral=True)
            return

        if response.status_code == 200:
            data = response.json().get("data", {})
            embed = discord.Embed(title="💳 Wallet Balance", color=discord.Color.green())
            embed.add_field(name="Username", value=data.get("username"), inline=True)
            embed.add_field(name="Balance", value=f"${data.get('balance')}", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to fetch balance: {response.text}", ephemeral=True)

    @discord.ui.button(label="🛒 Buy Accounts", style=discord.ButtonStyle.success, custom_id="btn_buy")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        try:
            response = await asyncio.to_thread(
                requests.get, f"{API_BASE}/stock", headers=HEADERS, timeout=10
            )
        except Exception:
            await interaction.response.send_message("❌ Stock check request timed out.", ephemeral=True)
            return

        if response.status_code == 200:
            categories = response.json().get("data", {}).get("categories", [])
            view = BuyDropdownView(categories)
            await interaction.response.send_message("Select the category you want to buy from below:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("Failed to fetch categories for buying.", ephemeral=True)

# --- Bot Setup ---
class MogBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(MogControlView())
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

client = MogBot()

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.tree.command(name="panel", description="Deploy the interactive Mog Alts control panel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚡ Mog Alts Control Center",
        description="Click the buttons below to check stock, look up your balance, or instantly buy accounts through menus.",
        color=discord.Color.dark_embed()
    )
    await interaction.response.send_message(embed=embed, view=MogControlView())

client.run(TOKEN)