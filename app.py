import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from functools import wraps
import string

# ==================== 機器人設定 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='/', intents=intents)

# ==================== 資料存儲 ====================
DATA_FILE = 'bot_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': {},
        'invite_codes': {},
        'redemption_codes': {},
        'verification_channel': None,
        'verified_role': None
    }

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ==================== 用戶初始化 ====================
def init_user(user_id: int):
    user_id = str(user_id)
    if user_id not in data['users']:
        data['users'][user_id] = {
            'game_points': 0,
            'activity_points': 0,
            'invite_code': generate_invite_code(),
            'invited_by': None,
            'invited_users': [],
            'last_checkin': None,
            'checkin_streak': 0,
            'weekly_checkin': [False] * 7,
            'gear': {
                'attack': 0,
                'defense': 0,
                'hp': 100
            },
            'mineral_level': 0,
            'mineral_last_claim': None,
            'lottery_tickets': [],
            'redemption_history': {}
        }
        save_data()

def generate_invite_code():
    """生成8位隨機邀請碼"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in data['invite_codes']:
            return code

# ==================== 權限檢查裝飾器 ====================
def require_verified():
    """要求用戶已通過驗證"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not data.get('verified_role'):
            await interaction.response.send_message("❌ 尚未設置驗證身分組！", ephemeral=True)
            return False
        
        role = interaction.guild.get_role(int(data['verified_role']))
        if not role or role not in interaction.user.roles:
            await interaction.response.send_message(
                "🚫 **你尚未通過驗證！**\n\n"
                "請先在驗證頻道提交推文截圖\n"
                "等待管理員審核通過後即可使用機器人功能",
                ephemeral=True
            )
            return False
        return True
    
    return app_commands.check(predicate)

# ==================== 新人驗證系統 ====================
@bot.event
async def on_raw_reaction_add(payload):
    """監聽管理員的 ✅ 反應"""
    if payload.user_id == bot.user.id:
        return
    
    if str(payload.emoji) != "✅":
        return
    
    # 檢查是否在驗證頻道
    if data.get('verification_channel') != str(payload.channel_id):
        return
    
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    
    # 檢查是否為管理員
    if not member.guild_permissions.administrator:
        return
    
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    
    # 獲取發文者
    author = message.author
    
    # 獲取驗證身分組
    verified_role_id = data.get('verified_role')
    if not verified_role_id:
        await channel.send("❌ 尚未設置驗證身分組！請使用 `/set_verified_role` 設置")
        return
    
    verified_role = guild.get_role(int(verified_role_id))
    if not verified_role:
        await channel.send("❌ 找不到驗證身分組！")
        return
    
    # 給予身分組
    try:
        await author.add_roles(verified_role)
        await channel.send(
            f"✅ {author.mention} 已通過驗證！\n"
            f"現在可以使用所有機器人功能了！"
        )
        
        # 私訊通知
        try:
            await author.send(
                f"🎉 **恭喜通過驗證！**\n\n"
                f"你現在可以使用以下功能：\n"
                f"• `/my_invite` - 查看你的邀請碼\n"
                f"• `/checkin` - 每日打卡\n"
                f"• `/game` - 遊戲系統\n"
                f"• `/transfer` - 轉帳積分\n"
                f"• 以及更多功能！\n\n"
                f"輸入 `/help` 查看完整指令列表"
            )
        except:
            pass
            
    except Exception as e:
        await channel.send(f"❌ 給予身分組時發生錯誤：{str(e)}")

@bot.tree.command(name="set_verification_channel", description="[管理員] 設置任務提交頻道")
@app_commands.describe(channel="任務提交頻道")
async def set_verification_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    data['verification_channel'] = str(channel.id)
    save_data()
    
    await interaction.response.send_message(
        f"✅ 已設置任務提交頻道為 {channel.mention}\n"
        f"新人可在此頻道提交推文截圖，管理員按 ✅ 即可給予驗證身分組"
    )

@bot.tree.command(name="set_verified_role", description="[管理員] 設置驗證通過後的身分組")
@app_commands.describe(role="驗證身分組")
async def set_verified_role(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    data['verified_role'] = str(role.id)
    save_data()
    
    await interaction.response.send_message(
        f"✅ 已設置驗證身分組為 {role.mention}\n"
        f"通過驗證的用戶將自動獲得此身分組"
    )

# ==================== 邀請系統 ====================
@bot.tree.command(name="my_invite", description="查看我的邀請碼和邀請記錄")
@require_verified()
async def my_invite(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    invite_code = user_data['invite_code']
    invited_users = user_data['invited_users']
    invited_count = len(invited_users)
    
    # 計算邀請獎勵
    invite_rewards = (invited_count // 2) * 10
    
    embed = discord.Embed(
        title="📨 我的邀請系統",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎫 我的邀請碼",
        value=f"`{invite_code}`",
        inline=False
    )
    
    embed.add_field(
        name="👥 已邀請人數",
        value=f"{invited_count} 人",
        inline=True
    )
    
    embed.add_field(
        name="🎁 邀請獎勵",
        value=f"{invite_rewards} 積分（每2人）",
        inline=True
    )
    
    if invited_users:
        users_text = ""
        for user_id in invited_users[:10]:
            try:
                user = await bot.fetch_user(int(user_id))
                users_text += f"• {user.name}\n"
            except:
                users_text += f"• ID: {user_id}\n"
        
        embed.add_field(
            name="📋 邀請列表",
            value=users_text or "無",
            inline=False
        )
    
    embed.add_field(
        name="💡 使用說明",
        value="將你的邀請碼分享給朋友\n他們使用 `/use_invite` 輸入即可",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="use_invite", description="輸入別人的邀請碼")
@require_verified()
@app_commands.describe(code="邀請碼")
async def use_invite(interaction: discord.Interaction, code: str):
    init_user(interaction.user.id)
    user_id = str(interaction.user.id)
    user_data = data['users'][user_id]
    
    if user_data['invited_by']:
        await interaction.response.send_message(
            "❌ 你已經使用過邀請碼了！每人只能使用一次",
            ephemeral=True
        )
        return
    
    inviter_id = None
    for uid, udata in data['users'].items():
        if udata['invite_code'] == code.upper():
            inviter_id = uid
            break
    
    if not inviter_id:
        await interaction.response.send_message(
            "❌ 邀請碼不存在！請確認邀請碼是否正確",
            ephemeral=True
        )
        return
    
    if inviter_id == user_id:
        await interaction.response.send_message(
            "❌ 不能使用自己的邀請碼！",
            ephemeral=True
        )
        return
    
    user_data['invited_by'] = inviter_id
    data['users'][inviter_id]['invited_users'].append(user_id)
    
    inviter_data = data['users'][inviter_id]
    invited_count = len(inviter_data['invited_users'])
    
    if invited_count % 2 == 0:
        inviter_data['activity_points'] += 10
        
        try:
            inviter = await bot.fetch_user(int(inviter_id))
            await inviter.send(
                f"🎉 **邀請獎勵！**\n\n"
                f"你已邀請 {invited_count} 位成員！\n"
                f"獲得獎勵：10 活動積分\n"
                f"當前活動積分：{inviter_data['activity_points']}"
            )
        except:
            pass
    
    save_data()
    
    await interaction.response.send_message(
        f"✅ **成功使用邀請碼！**\n\n"
        f"邀請者將在達到2人時獲得積分獎勵"
    )

# ==================== 打卡系統 ====================
@bot.tree.command(name="checkin", description="每日打卡領取積分")
@require_verified()
async def checkin(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_id = str(interaction.user.id)
    user_data = data['users'][user_id]
    
    today = datetime.now().date()
    last_checkin = user_data.get('last_checkin')
    
    if last_checkin:
        last_date = datetime.fromisoformat(last_checkin).date()
        if last_date == today:
            await interaction.response.send_message(
                "⏰ 你今天已經打卡過了！明天再來吧",
                ephemeral=True
            )
            return
        
        yesterday = today - timedelta(days=1)
        if last_date == yesterday:
            user_data['checkin_streak'] += 1
        else:
            user_data['checkin_streak'] = 1
            user_data['weekly_checkin'] = [False] * 7
    else:
        user_data['checkin_streak'] = 1
        user_data['weekly_checkin'] = [False] * 7
    
    user_data['last_checkin'] = datetime.now().isoformat()
    weekday = today.weekday()
    user_data['weekly_checkin'][weekday] = True
    
    game_reward = 5
    activity_reward = 5
    
    streak_bonus = min(user_data['checkin_streak'], 7)
    game_reward += streak_bonus
    activity_reward += streak_bonus
    
    weekly_bonus = 0
    if all(user_data['weekly_checkin']):
        weekly_bonus = 20
        game_reward += weekly_bonus
        activity_reward += weekly_bonus
        user_data['weekly_checkin'] = [False] * 7
    
    user_data['game_points'] += game_reward
    user_data['activity_points'] += activity_reward
    
    save_data()
    
    embed = discord.Embed(
        title="✅ 打卡成功！",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="🎮 遊戲積分",
        value=f"+{game_reward}",
        inline=True
    )
    
    embed.add_field(
        name="🎯 活動積分",
        value=f"+{activity_reward}",
        inline=True
    )
    
    embed.add_field(
        name="🔥 連續打卡",
        value=f"{user_data['checkin_streak']} 天",
        inline=True
    )
    
    week_progress = "".join(["✅" if x else "⬜" for x in user_data['weekly_checkin']])
    embed.add_field(
        name="📅 本週進度",
        value=f"{week_progress}\n{'🎁 已領取全勤獎勵！' if weekly_bonus > 0 else '連續7天打卡可獲得全勤獎勵'}",
        inline=False
    )
    
    embed.add_field(
        name="💰 當前積分",
        value=f"遊戲：{user_data['game_points']} | 活動：{user_data['activity_points']}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ==================== 遊戲系統 ====================
class GameMenu(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
    
    @discord.ui.button(label="💣 踩地雷", style=discord.ButtonStyle.primary)
    async def minesweeper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        await interaction.response.send_message("請使用 `/minesweeper` 開始踩地雷遊戲", ephemeral=True)
    
    @discord.ui.button(label="⛏️ 礦產", style=discord.ButtonStyle.success)
    async def mineral_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        await interaction.response.send_message("請使用 `/mineral` 開始礦產系統", ephemeral=True)

@bot.tree.command(name="game", description="遊戲選單")
@require_verified()
async def game(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    embed = discord.Embed(
        title="🎮 遊戲中心",
        description="選擇你想玩的遊戲",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="💰 你的積分",
        value=f"🎮 遊戲積分：{user_data['game_points']}\n🎯 活動積分：{user_data['activity_points']}",
        inline=False
    )
    
    embed.add_field(
        name="🎲 可用遊戲",
        value=(
            "💣 **踩地雷** - 高風險高回報\n"
            "⛏️ **礦產** - 被動收入系統"
        ),
        inline=False
    )
    
    view = GameMenu(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="minesweeper", description="踩地雷遊戲")
@require_verified()
@app_commands.describe(
    amount="下注金額",
    point_type="使用的積分類型"
)
@app_commands.choices(point_type=[
    app_commands.Choice(name="遊戲積分", value="game"),
    app_commands.Choice(name="活動積分", value="activity")
])
async def minesweeper(interaction: discord.Interaction, amount: int, point_type: app_commands.Choice[str]):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    if point_type.value == "game":
        if user_data['game_points'] < amount:
            await interaction.response.send_message(
                f"❌ 遊戲積分不足！你有 {user_data['game_points']} 積分",
                ephemeral=True
            )
            return
    else:
        if user_data['activity_points'] < amount:
            await interaction.response.send_message(
                f"❌ 活動積分不足！你有 {user_data['activity_points']} 積分",
                ephemeral=True
            )
            return
    
    await interaction.response.send_message(
        f"🎮 踩地雷遊戲開始！\n下注：{amount} {'遊戲' if point_type.value == 'game' else '活動'}積分\n"
        f"（簡化版本，實際遊戲邏輯需要進一步開發）"
    )

# ==================== 轉帳系統 ====================
@bot.tree.command(name="transfer", description="轉帳積分給其他玩家")
@require_verified()
@app_commands.describe(
    user="要轉帳的玩家",
    amount="轉帳金額",
    point_type="積分類型"
)
@app_commands.choices(point_type=[
    app_commands.Choice(name="遊戲積分", value="game"),
    app_commands.Choice(name="活動積分", value="activity")
])
async def transfer(interaction: discord.Interaction, user: discord.User, amount: int, point_type: app_commands.Choice[str]):
    if amount <= 0:
        await interaction.response.send_message("❌ 轉帳金額必須大於0！", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ 不能轉帳給自己！", ephemeral=True)
        return
    
    init_user(interaction.user.id)
    init_user(user.id)
    
    sender_data = data['users'][str(interaction.user.id)]
    receiver_data = data['users'][str(user.id)]
    
    point_name = "遊戲積分" if point_type.value == "game" else "活動積分"
    point_key = "game_points" if point_type.value == "game" else "activity_points"
    
    if sender_data[point_key] < amount:
        await interaction.response.send_message(
            f"❌ {point_name}不足！你有 {sender_data[point_key]} 積分",
            ephemeral=True
        )
        return
    
    fee = int(amount * 0.05)
    actual_amount = amount - fee
    
    sender_data[point_key] -= amount
    receiver_data[point_key] += actual_amount
    
    save_data()
    
    await interaction.response.send_message(
        f"✅ **轉帳成功！**\n\n"
        f"轉給：{user.mention}\n"
        f"類型：{point_name}\n"
        f"金額：{amount}\n"
        f"手續費：{fee} (5%)\n"
        f"實收：{actual_amount}\n\n"
        f"你的剩餘{point_name}：{sender_data[point_key]}"
    )

# ==================== 積分兌換系統（含序號池）====================
@bot.tree.command(name="add_redeem_code", description="[管理員] 新增兌換碼（給予積分）")
@app_commands.describe(
    code="兌換碼",
    reward_type="獎勵類型",
    reward_amount="獎勵數量",
    max_uses="可兌換次數（-1=無限）",
    duration="有效期限"
)
@app_commands.choices(
    reward_type=[
        app_commands.Choice(name="遊戲積分", value="game"),
        app_commands.Choice(name="活動積分", value="activity")
    ],
    duration=[
        app_commands.Choice(name="永久", value="permanent"),
        app_commands.Choice(name="每日", value="daily"),
        app_commands.Choice(name="每週", value="weekly"),
        app_commands.Choice(name="每月", value="monthly")
    ]
)
async def add_redeem_code(
    interaction: discord.Interaction,
    code: str,
    reward_type: app_commands.Choice[str],
    reward_amount: int,
    max_uses: int,
    duration: app_commands.Choice[str]
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼已存在！", ephemeral=True)
        return
    
    data['redemption_codes'][code] = {
        'reward_type': reward_type.value,
        'reward_amount': reward_amount,
        'max_uses': max_uses,
        'current_uses': 0,
        'duration': duration.value,
        'used_by': {}
    }
    
    save_data()
    
    await interaction.response.send_message(
        f"✅ **兌換碼新增成功！**\n\n"
        f"代碼：`{code}`\n"
        f"獎勵：{reward_amount} {'遊戲' if reward_type.value == 'game' else '活動'}積分\n"
        f"次數限制：{max_uses if max_uses > 0 else '無限'}\n"
        f"有效期：{duration.name}"
    )

@bot.tree.command(name="add_serial_code", description="[管理員] 新增序號池兌換碼（派發序號）")
@app_commands.describe(
    code="兌換碼",
    serials="序號列表（用逗號分隔，例如：KEY1,KEY2,KEY3）",
    description="序號描述（例如：Steam激活碼）",
    duration="有效期限"
)
@app_commands.choices(
    duration=[
        app_commands.Choice(name="永久", value="permanent"),
        app_commands.Choice(name="每日", value="daily"),
        app_commands.Choice(name="每週", value="weekly"),
        app_commands.Choice(name="每月", value="monthly")
    ]
)
async def add_serial_code(
    interaction: discord.Interaction,
    code: str,
    serials: str,
    description: str,
    duration: app_commands.Choice[str]
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼已存在！", ephemeral=True)
        return
    
    serial_list = [s.strip() for s in serials.split(',') if s.strip()]
    
    if not serial_list:
        await interaction.response.send_message("❌ 請提供至少一個序號！", ephemeral=True)
        return
    
    data['redemption_codes'][code] = {
        'reward_type': 'serial',
        'reward_amount': 0,
        'max_uses': len(serial_list),
        'current_uses': 0,
        'duration': duration.value,
        'used_by': {},
        'serial_pool': serial_list,
        'serial_used': {},
        'serial_description': description
    }
    
    save_data()
    
    preview = '\n'.join(serial_list[:5])
    if len(serial_list) > 5:
        preview += f'\n... 還有 {len(serial_list) - 5} 個'
    
    await interaction.response.send_message(
        f"✅ **序號池兌換碼新增成功！**\n\n"
        f"代碼：`{code}`\n"
        f"類型：序號派發\n"
        f"描述：{description}\n"
        f"序號數量：{len(serial_list)}\n"
        f"有效期：{duration.name}\n\n"
        f"序號預覽：\n```\n{preview}\n```"
    )

@bot.tree.command(name="add_serials", description="[管理員] 為現有序號池補充序號")
@app_commands.describe(
    code="兌換碼",
    serials="要補充的序號（用逗號分隔）"
)
async def add_serials(
    interaction: discord.Interaction,
    code: str,
    serials: str
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code not in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼不存在！", ephemeral=True)
        return
    
    code_data = data['redemption_codes'][code]
    
    if code_data['reward_type'] != 'serial':
        await interaction.response.send_message("❌ 此兌換碼不是序號池類型！", ephemeral=True)
        return
    
    new_serials = [s.strip() for s in serials.split(',') if s.strip()]
    
    if not new_serials:
        await interaction.response.send_message("❌ 請提供至少一個序號！", ephemeral=True)
        return
    
    code_data['serial_pool'].extend(new_serials)
    code_data['max_uses'] = len(code_data['serial_pool'])
    
    save_data()
    
    await interaction.response.send_message(
        f"✅ **序號補充成功！**\n\n"
        f"代碼：`{code}`\n"
        f"新增數量：{len(new_serials)}\n"
        f"當前總數：{len(code_data['serial_pool'])}\n"
        f"已使用：{code_data['current_uses']}\n"
        f"剩餘：{len(code_data['serial_pool']) - code_data['current_uses']}"
    )

@bot.tree.command(name="redeem_status", description="[管理員] 查看兌換碼使用狀態")
@app_commands.describe(code="兌換碼")
async def redeem_status(interaction: discord.Interaction, code: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code not in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼不存在！", ephemeral=True)
        return
    
    code_data = data['redemption_codes'][code]
    
    embed = discord.Embed(
        title=f"🔍 兌換碼狀態：{code}",
        color=discord.Color.blue()
    )
    
    if code_data['reward_type'] == 'serial':
        remaining = len(code_data['serial_pool']) - code_data['current_uses']
        
        embed.add_field(
            name="📦 類型",
            value=f"序號派發\n{code_data['serial_description']}",
            inline=False
        )
        
        embed.add_field(
            name="📊 使用情況",
            value=f"已使用：{code_data['current_uses']}/{len(code_data['serial_pool'])}\n剩餘：{remaining}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ 有效期",
            value=code_data['duration'],
            inline=True
        )
        
        if remaining > 0:
            remaining_serials = code_data['serial_pool'][code_data['current_uses']:]
            preview = '\n'.join(remaining_serials[:5])
            if len(remaining_serials) > 5:
                preview += f"\n... 還有 {len(remaining_serials) - 5} 個"
            
            embed.add_field(
                name="📋 剩餘序號預覽",
                value=f"```\n{preview}\n```",
                inline=False
            )
        
        if code_data['serial_used']:
            used_text = ""
            count = 0
            for user_id, serial in list(code_data['serial_used'].items())[:5]:
                try:
                    user = await bot.fetch_user(int(user_id))
                    used_text += f"• {user.name}: `{serial}`\n"
                    count += 1
                except:
                    pass
            
            if count > 0:
                if len(code_data['serial_used']) > 5:
                    used_text += f"\n... 還有 {len(code_data['serial_used']) - 5} 筆記錄"
                
                embed.add_field(
                    name="📝 派發記錄",
                    value=used_text,
                    inline=False
                )
    
    else:
        embed.add_field(
            name="💰 獎勵",
            value=f"{code_data['reward_amount']} {'遊戲' if code_data['reward_type'] == 'game' else '活動'}積分",
            inline=True
        )
        
        embed.add_field(
            name="📊 使用情況",
            value=f"{code_data['current_uses']}/{code_data['max_uses'] if code_data['max_uses'] > 0 else '無限'}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ 有效期",
            value=code_data['duration'],
            inline=True
        )
        
        if code_data['used_by']:
            users_text = ""
            count = 0
            for user_id in list(code_data['used_by'].keys())[:10]:
                try:
                    user = await bot.fetch_user(int(user_id))
                    users_text += f"• {user.name}\n"
                    count += 1
                except:
                    pass
            
            if count > 0:
                if len(code_data['used_by']) > 10:
                    users_text += f"\n... 還有 {len(code_data['used_by']) - 10} 人"
                
                embed.add_field(
                    name="👥 使用者列表",
                    value=users_text,
                    inline=False
                )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="list_redeem_codes", description="[管理員] 列出所有兌換碼")
async def list_redeem_codes(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if not data['redemption_codes']:
        await interaction.response.send_message("目前沒有任何兌換碼", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 所有兌換碼列表",
        color=discord.Color.gold()
    )
    
    for code, code_data in data['redemption_codes'].items():
        if code_data['reward_type'] == 'serial':
            remaining = len(code_data['serial_pool']) - code_data['current_uses']
            value = (
                f"類型：📦 序號派發\n"
                f"描述：{code_data['serial_description']}\n"
                f"剩餘：{remaining}/{len(code_data['serial_pool'])}"
            )
        else:
            reward_name = "遊戲積分" if code_data['reward_type'] == "game" else "活動積分"
            value = (
                f"類型：💰 {reward_name}\n"
                f"獎勵：{code_data['reward_amount']}\n"
                f"使用：{code_data['current_uses']}/{code_data['max_uses'] if code_data['max_uses'] > 0 else '無限'}"
            )
        
        embed.add_field(
            name=f"`{code}`",
            value=value,
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeem", description="兌換序號")
@require_verified()
@app_commands.describe(code="兌換碼")
async def redeem(interaction: discord.Interaction, code: str):
    init_user(interaction.user.id)
    user_id = str(interaction.user.id)
    user_data = data['users'][user_id]
    
    if code not in data['redemption_codes']:
        await interaction.response.send_message("❌ 兌換碼不存在！", ephemeral=True)
        return
    
    code_data = data['redemption_codes'][code]
    
    if code_data['reward_type'] == 'serial':
        if code_data['current_uses'] >= len(code_data['serial_pool']):
            await interaction.response.send_message("❌ 序號已全部發完！", ephemeral=True)
            return
    else:
        if code_data['max_uses'] > 0 and code_data['current_uses'] >= code_data['max_uses']:
            await interaction.response.send_message("❌ 此兌換碼已達使用上限！", ephemeral=True)
            return
    
    duration = code_data['duration']
    now = datetime.now()
    
    if user_id in code_data['used_by']:
        last_use = datetime.fromisoformat(code_data['used_by'][user_id])
        
        if duration == "daily":
            if (now - last_use).days < 1:
                await interaction.response.send_message("❌ 此兌換碼每日只能使用一次！", ephemeral=True)
                return
        elif duration == "weekly":
            if (now - last_use).days < 7:
                await interaction.response.send_message("❌ 此兌換碼每週只能使用一次！", ephemeral=True)
                return
        elif duration == "monthly":
            if (now - last_use).days < 30:
                await interaction.response.send_message("❌ 此兌換碼每月只能使用一次！", ephemeral=True)
                return
        elif duration == "permanent":
            await interaction.response.send_message("❌ 此兌換碼你已經使用過了！", ephemeral=True)
            return
    
    reward_type = code_data['reward_type']
    
    if reward_type == 'serial':
        serial_index = code_data['current_uses']
        assigned_serial = code_data['serial_pool'][serial_index]
        
        code_data['used_by'][user_id] = now.isoformat()
        code_data['serial_used'][user_id] = assigned_serial
        code_data['current_uses'] += 1
        
        save_data()
        
        try:
            await interaction.user.send(
                f"🎁 **兌換成功！**\n\n"
                f"你獲得了：{code_data['serial_description']}\n\n"
                f"序號：`{assigned_serial}`\n\n"
                f"⚠️ 請妥善保管你的序號，此訊息不會再次顯示！"
            )
            
            await interaction.response.send_message(
                f"✅ **兌換成功！**\n\n"
                f"你的序號已通過私訊發送給你！\n"
                f"請查看私訊並妥善保管序號",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ **兌換成功！**\n\n"
                f"類型：{code_data['serial_description']}\n"
                f"序號：`{assigned_serial}`\n\n"
                f"⚠️ 請立即複製並保存你的序號！\n"
                f"💡 建議開啟私訊功能，以便接收未來的序號",
                ephemeral=True
            )
    
    else:
        reward_amount = code_data['reward_amount']
        
        if reward_type == "game":
            user_data['game_points'] += reward_amount
            point_name = "遊戲積分"
        else:
            user_data['activity_points'] += reward_amount
            point_name = "活動積分"
        
        code_data['used_by'][user_id] = now.isoformat()
        code_data['current_uses'] += 1
        
        save_data()
        
        await interaction.response.send_message(
            f"✅ **兌換成功！**\n\n"
            f"獲得：{reward_amount} {point_name}\n"
            f"當前{point_name}：{user_data[f'{reward_type}_points']}",
            ephemeral=True
        )

@bot.tree.command(name="my_serials", description="查看我已兌換的序號")
@require_verified()
async def my_serials(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_id = str(interaction.user.id)
    
    my_serials = []
    
    for code, code_data in data['redemption_codes'].items():
        if code_data['reward_type'] == 'serial' and user_id in code_data['serial_used']:
            my_serials.append({
                'code': code,
                'description': code_data['serial_description'],
                'serial': code_data['serial_used'][user_id],
                'date': code_data['used_by'][user_id]
            })
    
    if not my_serials:
        await interaction.response.send_message(
            "你還沒有兌換過任何序號",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🎫 我的序號記錄",
        description="以下是你已兌換的所有序號",
        color=discord.Color.green()
    )
    
    for item in my_serials:
        date = datetime.fromisoformat(item['date']).strftime('%Y-%m-%d %H:%M')
        embed.add_field(
            name=f"{item['description']}",
            value=f"兌換碼：`{item['code']}`\n序號：`{item['serial']}`\n兌換時間：{date}",
            inline=False
        )
    
    embed.set_footer(text="⚠️ 請妥善保管你的序號")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== 戰鬥系統 ====================
@bot.tree.command(name="upgrade_gear", description="提升戰鬥屬性")
@require_verified()
@app_commands.describe(
    stat="要提升的屬性",
    amount="提升點數",
    point_type="使用的積分"
)
@app_commands.choices(
    stat=[
        app_commands.Choice(name="攻擊力", value="attack"),
        app_commands.Choice(name="防禦力", value="defense"),
        app_commands.Choice(name="生命值", value="hp")
    ],
    point_type=[
        app_commands.Choice(name="遊戲積分", value="game"),
        app_commands.Choice(name="活動積分", value="activity")
    ]
)
async def upgrade_gear(
    interaction: discord.Interaction,
    stat: app_commands.Choice[str],
    amount: int,
    point_type: app_commands.Choice[str]
):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    cost = amount * 10
    
    point_key = f"{point_type.value}_points"
    if user_data[point_key] < cost:
        await interaction.response.send_message(
            f"❌ 積分不足！需要 {cost} {'遊戲' if point_type.value == 'game' else '活動'}積分",
            ephemeral=True
        )
        return
    
    user_data[point_key] -= cost
    user_data['gear'][stat.value] += amount
    
    save_data()
    
    gear = user_data['gear']
    
    embed = discord.Embed(
        title="⚔️ 屬性提升成功！",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="💪 當前屬性",
        value=f"攻擊：{gear['attack']}\n防禦：{gear['defense']}\n生命：{gear['hp']}",
        inline=False
    )
    
    embed.add_field(
        name="💰 剩餘積分",
        value=f"遊戲：{user_data['game_points']}\n活動：{user_data['activity_points']}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="battle", description="與其他玩家戰鬥")
@require_verified()
@app_commands.describe(opponent="對手")
async def battle(interaction: discord.Interaction, opponent: discord.User):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("❌ 不能與自己戰鬥！", ephemeral=True)
        return
    
    init_user(interaction.user.id)
    init_user(opponent.id)
    
    attacker_data = data['users'][str(interaction.user.id)]
    defender_data = data['users'][str(opponent.id)]
    
    attacker_gear = attacker_data['gear']
    defender_gear = defender_data['gear']
    
    attacker_power = attacker_gear['attack'] + attacker_gear['defense'] + attacker_gear['hp']
    defender_power = defender_gear['attack'] + defender_gear['defense'] + defender_gear['hp']
    
    attacker_roll = random.randint(1, 100)
    defender_roll = random.randint(1, 100)
    
    attacker_total = attacker_power + attacker_roll
    defender_total = defender_power + defender_roll
    
    if attacker_total > defender_total:
        winner = interaction.user
        loser = opponent
        winner_data = attacker_data
        loser_data = defender_data
    else:
        winner = opponent
        loser = interaction.user
        winner_data = defender_data
        loser_data = attacker_data
    
    stolen = int(loser_data['game_points'] * 0.05)
    winner_data['game_points'] += stolen
    loser_data['game_points'] -= stolen
    
    save_data()
    
    embed = discord.Embed(
        title="⚔️ 戰鬥結果",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="🏆 勝利者",
        value=winner.mention,
        inline=True
    )
    
    embed.add_field(
        name="💀 失敗者",
        value=loser.mention,
        inline=True
    )
    
    embed.add_field(
        name="💰 戰利品",
        value=f"{stolen} 遊戲積分",
        inline=False
    )
    
    embed.add_field(
        name="📊 戰鬥詳情",
        value=(
            f"{interaction.user.mention}: {attacker_power} + 🎲{attacker_roll} = {attacker_total}\n"
            f"{opponent.mention}: {defender_power} + 🎲{defender_roll} = {defender_total}"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ==================== 礦產系統 ====================
@bot.tree.command(name="mineral", description="礦產系統 - 被動收入")
@require_verified()
async def mineral(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    level = user_data['mineral_level']
    daily_income = level * 10
    
    embed = discord.Embed(
        title="⛏️ 礦產系統",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="當前等級",
        value=f"Lv.{level}",
        inline=True
    )
    
    embed.add_field(
        name="每日收入",
        value=f"{daily_income} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="升級費用",
        value=f"{(level + 1) * 100} 遊戲積分",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

# ==================== Help 指令 ====================
@bot.tree.command(name="help", description="查看機器人使用指南")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 機器人使用指南",
        description="以下是所有可用功能",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔰 新人驗證",
        value=(
            "1. 在驗證頻道貼推文截圖\n"
            "2. 等待管理員按 ✅\n"
            "3. 獲得驗證身分組後即可使用所有功能"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📨 邀請系統",
        value=(
            "`/my_invite` - 查看我的邀請碼\n"
            "`/use_invite` - 使用別人的邀請碼\n"
            "💡 每邀請2人獲得10活動積分"
        ),
        inline=False
    )
    
    embed.add_field(
        name="✅ 打卡系統",
        value=(
            "`/checkin` - 每日打卡\n"
            "💡 每天獲得遊戲+活動積分\n"
            "💡 連續打卡有加成\n"
            "💡 全週打卡有額外獎勵"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 遊戲系統",
        value=(
            "`/game` - 遊戲選單\n"
            "`/minesweeper` - 踩地雷\n"
            "💡 可使用遊戲積分或活動積分下注"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💸 轉帳系統",
        value=(
            "`/transfer` - 轉帳積分\n"
            "💡 手續費5%"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎁 兌換系統",
        value=(
            "`/redeem` - 兌換序號\n"
            "`/my_serials` - 查看我的序號\n"
            "💡 可兌換遊戲/活動積分或道具序號"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ 戰鬥系統",
        value=(
            "`/upgrade_gear` - 提升屬性\n"
            "`/battle` - 與玩家戰鬥\n"
            "💡 勝利者可獲得對方5%遊戲積分"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ==================== 啟動機器人 ====================
@bot.event
async def on_ready():
    print(f'✅ 機器人已登入: {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ 成功同步 {len(synced)} 個指令')
    except Exception as e:
        print(f'❌ 指令同步失敗: {e}')

# ==================== Token 設定 ====================
# # 方法1: 使用環境變數（推薦）
# import os
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# if not TOKEN:
#     print("❌ 錯誤: 找不到 DISCORD_BOT_TOKEN")
#     print("請確認:")
#     print("1. 已創建 .env 檔案")
#     print("2. .env 檔案中有 DISCORD_BOT_TOKEN=你的token")
#     print("3. 已安裝 python-dotenv (pip install python-dotenv)")
#     exit(1)

# bot.run(TOKEN)
# ==================== 啟動機器人 ====================
@bot.event
async def on_ready():
    print(f'✅ 機器人已登入: {bot.user}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ 成功同步 {len(synced)} 個指令')
    except Exception as e:
        print(f'❌ 指令同步失敗: {e}')

# 請在此處填入你的機器人 TOKEN

bot.run(TOKEN)