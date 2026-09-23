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