import discord
from discord.ext import commands
from discord import app_commands, Embed, File, Interaction, ButtonStyle
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# In-memory database (you should replace this with actual persistent storage)
reports = {}
flags = {}

STAFF_GUILD_ID = 1374139194766659664  # Replace with your staff server's guild ID
REPORT_CHANNEL_ID = 1374147501921140796  # Channel where initial reports go
ESCALATED_CHANNEL_ID = 1374147872542425088  # Channel for escalated reports
HANDLED_REPORTS_CHANNEL_ID = 1374147795610505236  # Channel for handled reports
ADDED_FLAGS_CHANNEL_ID = 1373776918318551132  # Channel for displaying added flags

class ReportModal(Modal, title="Report User"):
    def __init__(self):
        super().__init__()
        self.add_item(TextInput(label="Reported User ID", placeholder="123456789012345678"))
        self.add_item(TextInput(label="Reason", style=discord.TextStyle.paragraph))
        self.add_item(TextInput(label="Evidence Link", placeholder="https://..."))

    async def on_submit(self, interaction: Interaction):
        user_id = self.children[0].value
        reason = self.children[1].value
        evidence = self.children[2].value

        report_id = len(reports) + 1
        reports[report_id] = {
            'reporter_id': interaction.user.id,
            'reported_user_id': user_id,
            'reason': reason,
            'evidence': evidence,
            'status': 'Pending'
        }

        embed = Embed(title="New Report", color=discord.Color.orange())
        embed.add_field(name="Reported User ID", value=user_id, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Evidence", value=evidence, inline=False)
        embed.set_footer(text=f"Report ID: {report_id}")

        # Send to staff server
        staff_guild = bot.get_guild(STAFF_GUILD_ID)
        channel = staff_guild.get_channel(REPORT_CHANNEL_ID)
        msg = await channel.send(embed=embed, view=ReportActionView(report_id))
        await msg.create_thread(name=f"Report Discussion #{report_id}")

        await interaction.response.send_message("Your report has been submitted.", ephemeral=True)

class ReportActionView(View):
    def __init__(self, report_id):
        super().__init__(timeout=None)
        self.report_id = report_id

        self.add_item(Button(label="Request More Info", style=ButtonStyle.secondary, custom_id=f"more_info_{report_id}"))
        self.add_item(Button(label="Escalate Report", style=ButtonStyle.danger, custom_id=f"escalate_{report_id}"))
        self.add_item(Button(label="No Further Action", style=ButtonStyle.success, custom_id=f"no_action_{report_id}"))

    @discord.ui.button(label="Flag User", style=ButtonStyle.primary, custom_id="flag_user")
    async def flag_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(FlagUserModal(self.report_id))

class FlagUserModal(Modal, title="Flag User"):
    def __init__(self, report_id):
        super().__init__()
        self.report_id = report_id
        self.add_item(TextInput(label="Flag Reason", style=discord.TextStyle.paragraph))

    async def on_submit(self, interaction: Interaction):
        reason = self.children[0].value
        report = reports[self.report_id]
        user_id = report['reported_user_id']

        flags[user_id] = reason
        embed = Embed(title="User Flagged", color=discord.Color.red())
        embed.add_field(name="User ID", value=user_id, inline=False)
        embed.add_field(name="Reason", value=reason)
        channel = bot.get_channel(ADDED_FLAGS_CHANNEL_ID)
        await channel.send(embed=embed)

        # Mark report as handled
        report['status'] = 'Flagged'
        handled_channel = bot.get_channel(HANDLED_REPORTS_CHANNEL_ID)
        await handled_channel.send(embed=embed)

        reporter = await bot.fetch_user(report['reporter_id'])
        await reporter.send(f"Your report (ID: {self.report_id}) has been escalated and the user was flagged.")
        await interaction.response.send_message("User has been flagged.", ephemeral=True)

@bot.tree.command(name="report", description="Report a user")
async def report(interaction: Interaction):
    await interaction.response.send_modal(ReportModal())

@bot.tree.command(name="profile", description="View a user's profile and flag status")
@app_commands.describe(user_id="The Discord ID of the user to check")
async def profile(interaction: Interaction, user_id: str):
    embed = Embed(title=f"User Profile - {user_id}")
    flag = flags.get(user_id)
    if flag:
        embed.color = discord.Color.red()
        embed.add_field(name="Flagged", value=f"Yes - {flag}", inline=False)
        embed.set_image(url="https://example.com/flagged.png")
    else:
        embed.color = discord.Color.green()
        embed.add_field(name="Flagged", value="No", inline=False)
        embed.set_image(url="https://example.com/safe.png")

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")
