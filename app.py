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

# ==================== 管理員設定 ====================
ADMIN_USER_IDS = [
    775343433278816268,
]

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
            'game_points': 100,  # 初始遊戲積分
            'activity_points': 0,
            'invite_code': generate_invite_code(),
            'invited_by': None,
            'invited_users': [],
            'last_checkin': None,
            'checkin_streak': 0,
            'weekly_checkin': [False] * 7,
            'gear': {
                'attack': 10,
                'defense': 10,
                'hp': 100
            },
            'mineral_level': 0,
            'mineral_last_claim': None,
            'lottery_tickets': [],
            'redemption_history': {},
            'my_serials': [],
            'battle_stats': {
                'wins': 0,
                'losses': 0,
                'total_earned': 0,
                'total_lost': 0
            }
        }
        save_data()

def generate_invite_code():
    """生成8位隨機邀請碼"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in data['invite_codes']:
            return code

def generate_game_serial():
    """生成20碼遊戲序號（純文字格式，無短橫線）"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))

# ==================== 權限檢查裝飾器 ====================
def is_admin(interaction: discord.Interaction) -> bool:
    """檢查是否為管理員（Discord權限或自訂列表）"""
    if interaction.user.guild_permissions.administrator:
        return True
    if interaction.user.id in ADMIN_USER_IDS:
        return True
    return False

def require_verified():
    """要求用戶已通過驗證（管理員自動通過）"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if is_admin(interaction):
            return True
        
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
    
    if data.get('verification_channel') != str(payload.channel_id):
        return
    
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    
    if not (member.guild_permissions.administrator or member.id in ADMIN_USER_IDS):
        return
    
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    
    author = message.author
    
    verified_role_id = data.get('verified_role')
    if not verified_role_id:
        await channel.send("❌ 尚未設置驗證身分組！請使用 `/set_verified_role` 設置")
        return
    
    verified_role = guild.get_role(int(verified_role_id))
    if not verified_role:
        await channel.send("❌ 找不到驗證身分組！")
        return
    
    try:
        await author.add_roles(verified_role)
        await channel.send(
            f"✅ {author.mention} 已通過驗證！\n"
            f"現在可以使用所有機器人功能了！"
        )
        
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
    if not is_admin(interaction):
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
    if not is_admin(interaction):
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

# ==================== 完整踩地雷遊戲 ====================
class MinesweeperButton(discord.ui.Button):
    def __init__(self, x: int, y: int, is_mine: bool):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬜", row=y)
        self.x = x
        self.y = y
        self.is_mine = is_mine
        self.revealed = False
        self.flagged = False
    
    async def callback(self, interaction: discord.Interaction):
        view: MinesweeperView = self.view
        
        if interaction.user.id != view.player_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        
        if self.revealed or self.flagged:
            await interaction.response.send_message("此格已被翻開或標記！", ephemeral=True)
            return
        
        self.revealed = True
        
        if self.is_mine:
            # 踩到地雷
            self.label = "💣"
            self.style = discord.ButtonStyle.danger
            view.game_over = True
            view.won = False
            
            # 顯示所有地雷
            for button in view.children:
                if isinstance(button, MinesweeperButton) and button.is_mine:
                    button.label = "💣"
                    button.style = discord.ButtonStyle.danger
                    button.disabled = True
            
            # 扣除積分
            user_data = data['users'][str(view.player_id)]
            if view.point_type == "game":
                user_data['game_points'] -= view.bet_amount
            else:
                user_data['activity_points'] -= view.bet_amount
            save_data()
            
            embed = discord.Embed(
                title="💣 踩到地雷了！",
                description=f"你輸了 {view.bet_amount} {'遊戲' if view.point_type == 'game' else '活動'}積分",
                color=discord.Color.red()
            )
            embed.add_field(
                name="剩餘積分",
                value=f"{user_data['game_points'] if view.point_type == 'game' else user_data['activity_points']}",
                inline=False
            )
            
            for button in view.children:
                button.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
            
        else:
            # 安全格子
            mines_nearby = view.count_nearby_mines(self.x, self.y)
            self.label = str(mines_nearby) if mines_nearby > 0 else "✅"
            self.style = discord.ButtonStyle.success
            self.disabled = True
            
            view.safe_revealed += 1
            
            # 檢查是否獲勝
            if view.safe_revealed >= view.safe_cells:
                view.game_over = True
                view.won = True
                
                # 獲得獎勵
                multiplier = 1.5
                reward = int(view.bet_amount * multiplier)
                user_data = data['users'][str(view.player_id)]
                if view.point_type == "game":
                    user_data['game_points'] += reward
                else:
                    user_data['activity_points'] += reward
                save_data()
                
                embed = discord.Embed(
                    title="🎉 恭喜獲勝！",
                    description=f"你獲得了 {reward} {'遊戲' if view.point_type == 'game' else '活動'}積分！",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="當前積分",
                    value=f"{user_data['game_points'] if view.point_type == 'game' else user_data['activity_points']}",
                    inline=False
                )
                
                for button in view.children:
                    button.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=view)
                view.stop()
            else:
                await interaction.response.edit_message(view=view)

class MinesweeperView(discord.ui.View):
    def __init__(self, player_id: int, bet_amount: int, point_type: str, grid_size: int = 5, mine_count: int = 5):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.bet_amount = bet_amount
        self.point_type = point_type
        self.grid_size = grid_size
        self.mine_count = mine_count
        self.safe_cells = grid_size * grid_size - mine_count
        self.safe_revealed = 0
        self.game_over = False
        self.won = False
        
        # 生成地雷位置
        positions = [(x, y) for x in range(grid_size) for y in range(grid_size)]
        mine_positions = random.sample(positions, mine_count)
        
        # 創建按鈕
        for y in range(grid_size):
            for x in range(grid_size):
                is_mine = (x, y) in mine_positions
                button = MinesweeperButton(x, y, is_mine)
                self.add_item(button)
    
    def count_nearby_mines(self, x: int, y: int) -> int:
        """計算周圍8格的地雷數量"""
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                    for button in self.children:
                        if isinstance(button, MinesweeperButton):
                            if button.x == nx and button.y == ny and button.is_mine:
                                count += 1
        return count

@bot.tree.command(name="minesweeper", description="踩地雷遊戲 - 避開地雷翻開所有安全格")
@require_verified()
@app_commands.describe(
    amount="下注金額",
    point_type="使用的積分類型",
    difficulty="難度"
)
@app_commands.choices(
    point_type=[
        app_commands.Choice(name="遊戲積分", value="game"),
        app_commands.Choice(name="活動積分", value="activity")
    ],
    difficulty=[
        app_commands.Choice(name="簡單 (5x5, 5個雷)", value="easy"),
        app_commands.Choice(name="中等 (5x5, 8個雷)", value="medium"),
        app_commands.Choice(name="困難 (5x5, 12個雷)", value="hard")
    ]
)
async def minesweeper(
    interaction: discord.Interaction,
    amount: int,
    point_type: app_commands.Choice[str],
    difficulty: app_commands.Choice[str] = None
):
    if amount <= 0:
        await interaction.response.send_message("❌ 下注金額必須大於0！", ephemeral=True)
        return
    
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
    
    # 設定難度
    if difficulty is None:
        mine_count = 5
        diff_name = "簡單"
    elif difficulty.value == "easy":
        mine_count = 5
        diff_name = "簡單"
    elif difficulty.value == "medium":
        mine_count = 8
        diff_name = "中等"
    else:
        mine_count = 12
        diff_name = "困難"
    
    view = MinesweeperView(interaction.user.id, amount, point_type.value, grid_size=5, mine_count=mine_count)
    
    embed = discord.Embed(
        title="💣 踩地雷遊戲",
        description=(
            f"**難度：** {diff_name}\n"
            f"**地雷數量：** {mine_count}\n"
            f"**下注：** {amount} {'遊戲' if point_type.value == 'game' else '活動'}積分\n"
            f"**獎勵倍率：** 1.5x\n\n"
            f"點擊格子翻開，避開所有地雷即可獲勝！"
        ),
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, view=view)

# ==================== 完整礦產系統 ====================
@bot.tree.command(name="mineral", description="礦產系統 - 被動收入")
@require_verified()
async def mineral(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    level = user_data['mineral_level']
    hourly_income = level * 5  # 每級每小時5積分
    daily_income = hourly_income * 24
    upgrade_cost = (level + 1) * 100
    
    embed = discord.Embed(
        title="⛏️ 礦產系統",
        description="被動收入系統，每小時自動產生積分",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="📊 當前等級",
        value=f"Lv.{level}",
        inline=True
    )
    
    embed.add_field(
        name="💰 每小時收入",
        value=f"{hourly_income} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="📅 每日收入",
        value=f"{daily_income} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="⬆️ 升級費用",
        value=f"{upgrade_cost} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="💎 你的積分",
        value=f"{user_data['game_points']} 遊戲積分",
        inline=True
    )
    
    # 計算可領取的積分
    last_claim = user_data.get('mineral_last_claim')
    if last_claim and level > 0:
        last_claim_time = datetime.fromisoformat(last_claim)
        hours_passed = (datetime.now() - last_claim_time).total_seconds() / 3600
        claimable = int(hours_passed * hourly_income)
        
        embed.add_field(
            name="🎁 可領取",
            value=f"{claimable} 遊戲積分",
            inline=False
        )
    
    embed.add_field(
        name="💡 使用說明",
        value=(
            "• 使用 `/mineral_upgrade` 升級礦場\n"
            "• 使用 `/mineral_claim` 領取收益\n"
            "• 礦場會持續產生收益，記得定期領取！"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mineral_upgrade", description="升級礦場等級")
@require_verified()
async def mineral_upgrade(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    level = user_data['mineral_level']
    upgrade_cost = (level + 1) * 100
    
    if user_data['game_points'] < upgrade_cost:
        await interaction.response.send_message(
            f"❌ 遊戲積分不足！需要 {upgrade_cost} 積分，你有 {user_data['game_points']} 積分",
            ephemeral=True
        )
        return
    
    user_data['game_points'] -= upgrade_cost
    user_data['mineral_level'] += 1
    
    new_level = user_data['mineral_level']
    new_hourly = new_level * 5
    new_daily = new_hourly * 24
    
    save_data()
    
    embed = discord.Embed(
        title="⛏️ 礦場升級成功！",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="🆕 新等級",
        value=f"Lv.{new_level}",
        inline=True
    )
    
    embed.add_field(
        name="💰 新收入",
        value=f"每小時 {new_hourly} 積分\n每日 {new_daily} 積分",
        inline=True
    )
    
    embed.add_field(
        name="💎 剩餘積分",
        value=f"{user_data['game_points']} 遊戲積分",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mineral_claim", description="領取礦產收益")
@require_verified()
async def mineral_claim(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    level = user_data['mineral_level']
    
    if level == 0:
        await interaction.response.send_message(
            "❌ 你還沒有礦場！請先使用 `/mineral_upgrade` 升級",
            ephemeral=True
        )
        return
    
    last_claim = user_data.get('mineral_last_claim')
    now = datetime.now()
    
    if last_claim:
        last_claim_time = datetime.fromisoformat(last_claim)
        hours_passed = (now - last_claim_time).total_seconds() / 3600
        
        if hours_passed < 1:
            minutes_left = int((1 - hours_passed) * 60)
            await interaction.response.send_message(
                f"⏰ 請等待 {minutes_left} 分鐘後再領取！",
                ephemeral=True
            )
            return
        
        claimable = int(hours_passed * level * 5)
        max_claim = level * 5 * 24  # 最多累積24小時
        claimable = min(claimable, max_claim)
    else:
        claimable = 0
    
    user_data['game_points'] += claimable
    user_data['mineral_last_claim'] = now.isoformat()
    
    save_data()
    
    embed = discord.Embed(
        title="💎 領取成功！",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🎁 獲得",
        value=f"{claimable} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="💰 當前積分",
        value=f"{user_data['game_points']} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="⏰ 下次領取",
        value="1小時後",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# ==================== 遊戲選單 ====================
class GameMenu(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
    
    @discord.ui.button(label="💣 踩地雷", style=discord.ButtonStyle.primary)
    async def minesweeper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        await interaction.response.send_message(
            "請使用 `/minesweeper` 開始踩地雷遊戲\n"
            "可選擇下注金額、積分類型和難度！",
            ephemeral=True
        )
    
    @discord.ui.button(label="⛏️ 礦產", style=discord.ButtonStyle.success)
    async def mineral_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        await interaction.response.send_message(
            "請使用以下指令操作礦產系統：\n"
            "• `/mineral` - 查看礦場狀態\n"
            "• `/mineral_upgrade` - 升級礦場\n"
            "• `/mineral_claim` - 領取收益",
            ephemeral=True
        )
    
    @discord.ui.button(label="📊 我的資料", style=discord.ButtonStyle.secondary)
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
            return
        await interaction.response.send_message(
            "請使用 `/profile` 查看你的完整資料",
            ephemeral=True
        )

@bot.tree.command(name="game", description="遊戲中心")
@require_verified()
async def game(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_data = data['users'][str(interaction.user.id)]
    
    embed = discord.Embed(
        title="🎮 遊戲中心",
        description="選擇你想玩的遊戲或查看資料",
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
            "💣 **踩地雷** - 高風險高回報，1.5倍獎勵\n"
            "⛏️ **礦產** - 被動收入系統，持續產生積分"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📈 戰鬥統計",
        value=(
            f"勝場：{user_data.get('battle_stats', {}).get('wins', 0)}\n"
            f"敗場：{user_data.get('battle_stats', {}).get('losses', 0)}"
        ),
        inline=True
    )
    
    view = GameMenu(interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

# ==================== 個人資料 ====================
@bot.tree.command(name="profile", description="查看個人資料")
@require_verified()
async def profile(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    init_user(target_user.id)
    user_data = data['users'][str(target_user.id)]
    
    embed = discord.Embed(
        title=f"📊 {target_user.name} 的資料",
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    embed.add_field(
        name="💰 積分",
        value=f"🎮 遊戲：{user_data['game_points']}\n🎯 活動：{user_data['activity_points']}",
        inline=True
    )
    
    embed.add_field(
        name="⚔️ 屬性",
        value=f"攻擊：{user_data['gear']['attack']}\n防禦：{user_data['gear']['defense']}\n生命：{user_data['gear']['hp']}",
        inline=True
    )
    
    embed.add_field(
        name="⛏️ 礦場",
        value=f"等級：Lv.{user_data['mineral_level']}\n時收：{user_data['mineral_level'] * 5}",
        inline=True
    )
    
    embed.add_field(
        name="🔥 打卡",
        value=f"連續：{user_data['checkin_streak']}天",
        inline=True
    )
    
    embed.add_field(
        name="👥 邀請",
        value=f"已邀請：{len(user_data['invited_users'])}人",
        inline=True
    )
    
    battle_stats = user_data.get('battle_stats', {})
    total_battles = battle_stats.get('wins', 0) + battle_stats.get('losses', 0)
    win_rate = (battle_stats.get('wins', 0) / total_battles * 100) if total_battles > 0 else 0
    
    embed.add_field(
        name="⚔️ 戰鬥",
        value=f"勝率：{win_rate:.1f}%\n戰績：{battle_stats.get('wins', 0)}勝{battle_stats.get('losses', 0)}敗",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

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
    if not is_admin(interaction):
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

@bot.tree.command(name="add_serial_code", description="[管理員] 新增序號池兌換碼")
@app_commands.describe(
    code="兌換碼名稱",
    item_name="道具名稱（例如：遊戲激活碼、月卡序號）",
    quantity="序號數量（自動生成20碼序號）",
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
    item_name: str,
    quantity: int,
    duration: app_commands.Choice[str]
):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼已存在！", ephemeral=True)
        return
    
    if quantity <= 0 or quantity > 1000:
        await interaction.response.send_message("❌ 序號數量必須在 1-1000 之間！", ephemeral=True)
        return
    
    serial_pool = []
    for _ in range(quantity):
        serial_pool.append(generate_game_serial())
    
    data['redemption_codes'][code] = {
        'reward_type': 'serial',
        'item_name': item_name,
        'max_uses': quantity,
        'current_uses': 0,
        'duration': duration.value,
        'used_by': {},
        'serial_pool': serial_pool,
        'serial_assigned': {}
    }
    
    save_data()
    
    preview = '\n'.join(serial_pool[:3])
    if quantity > 3:
        preview += f'\n... 還有 {quantity - 3} 個'
    
    await interaction.response.send_message(
        f"✅ **序號池兌換碼新增成功！**\n\n"
        f"代碼：`{code}`\n"
        f"道具：{item_name}\n"
        f"序號數量：{quantity} 個（20碼格式）\n"
        f"有效期：{duration.name}\n\n"
        f"序號預覽：\n```\n{preview}\n```\n\n"
        f"💡 玩家使用 `/redeem {code}` 即可自動獲得一組序號"
    )

@bot.tree.command(name="add_custom_serials", description="[管理員] 手動新增自訂序號到序號池")
@app_commands.describe(
    code="兌換碼名稱",
    item_name="道具名稱",
    serials="序號列表（用逗號分隔，支援任意格式）",
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
async def add_custom_serials(
    interaction: discord.Interaction,
    code: str,
    item_name: str,
    serials: str,
    duration: app_commands.Choice[str]
):
    if not is_admin(interaction):
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
        'item_name': item_name,
        'max_uses': len(serial_list),
        'current_uses': 0,
        'duration': duration.value,
        'used_by': {},
        'serial_pool': serial_list,
        'serial_assigned': {}
    }
    
    save_data()
    
    preview = '\n'.join(serial_list[:5])
    if len(serial_list) > 5:
        preview += f'\n... 還有 {len(serial_list) - 5} 個'
    
    await interaction.response.send_message(
        f"✅ **自訂序號池新增成功！**\n\n"
        f"代碼：`{code}`\n"
        f"道具：{item_name}\n"
        f"序號數量：{len(serial_list)}\n"
        f"有效期：{duration.name}\n\n"
        f"序號預覽：\n```\n{preview}\n```"
    )

@bot.tree.command(name="append_serials", description="[管理員] 為現有序號池補充序號")
@app_commands.describe(
    code="兌換碼",
    quantity="要補充的數量（自動生成）",
    custom_serials="或手動輸入序號（用逗號分隔，優先使用此項）"
)
async def append_serials(
    interaction: discord.Interaction,
    code: str,
    quantity: int = 0,
    custom_serials: str = ""
):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code not in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼不存在！", ephemeral=True)
        return
    
    code_data = data['redemption_codes'][code]
    
    if code_data['reward_type'] != 'serial':
        await interaction.response.send_message("❌ 此兌換碼不是序號池類型！", ephemeral=True)
        return
    
    new_serials = []
    
    if custom_serials.strip():
        new_serials = [s.strip() for s in custom_serials.split(',') if s.strip()]
    elif quantity > 0:
        for _ in range(quantity):
            new_serials.append(generate_game_serial())
    else:
        await interaction.response.send_message(
            "❌ 請指定要生成的數量或提供自訂序號！",
            ephemeral=True
        )
        return
    
    code_data['serial_pool'].extend(new_serials)
    code_data['max_uses'] = len(code_data['serial_pool'])
    
    save_data()
    
    remaining = len(code_data['serial_pool']) - code_data['current_uses']
    
    await interaction.response.send_message(
        f"✅ **序號補充成功！**\n\n"
        f"代碼：`{code}`\n"
        f"新增數量：{len(new_serials)}\n"
        f"當前總數：{len(code_data['serial_pool'])}\n"
        f"已派發：{code_data['current_uses']}\n"
        f"剩餘可用：{remaining}"
    )

@bot.tree.command(name="redeem_status", description="[管理員] 查看兌換碼使用狀態")
@app_commands.describe(code="兌換碼")
async def redeem_status(interaction: discord.Interaction, code: str):
    if not is_admin(interaction):
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
            value=f"序號派發：{code_data['item_name']}",
            inline=False
        )
        
        embed.add_field(
            name="📊 使用情況",
            value=f"已派發：{code_data['current_uses']}/{len(code_data['serial_pool'])}\n剩餘：{remaining}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ 有效期",
            value=code_data['duration'],
            inline=True
        )
        
        if remaining > 0:
            remaining_serials = code_data['serial_pool'][code_data['current_uses']:]
            preview = '\n'.join(remaining_serials[:3])
            if len(remaining_serials) > 3:
                preview += f"\n... 還有 {len(remaining_serials) - 3} 個"
            
            embed.add_field(
                name="📋 剩餘序號預覽",
                value=f"```\n{preview}\n```",
                inline=False
            )
        
        if code_data['serial_assigned']:
            assigned_text = ""
            count = 0
            for user_id, serial in list(code_data['serial_assigned'].items())[:5]:
                try:
                    user = await bot.fetch_user(int(user_id))
                    assigned_text += f"• {user.name}: `{serial}`\n"
                    count += 1
                except:
                    pass
            
            if count > 0:
                if len(code_data['serial_assigned']) > 5:
                    assigned_text += f"\n... 還有 {len(code_data['serial_assigned']) - 5} 筆記錄"
                
                embed.add_field(
                    name="📝 派發記錄",
                    value=assigned_text,
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
    if not is_admin(interaction):
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
                f"道具：{code_data['item_name']}\n"
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

@bot.tree.command(name="redeem", description="兌換序號或積分")
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
        code_data['serial_assigned'][user_id] = assigned_serial
        code_data['current_uses'] += 1
        
        if 'my_serials' not in user_data:
            user_data['my_serials'] = []
        
        user_data['my_serials'].append({
            'code': code,
            'item_name': code_data['item_name'],
            'serial': assigned_serial,
            'redeemed_at': now.isoformat()
        })
        
        save_data()
        
        try:
            await interaction.user.send(
                f"🎁 **兌換成功！**\n\n"
                f"道具：{code_data['item_name']}\n"
                f"序號：`{assigned_serial}`\n\n"
                f"⚠️ 請妥善保管你的序號！\n"
                f"💡 使用 `/my_serials` 可隨時查看你的所有序號"
            )
            
            await interaction.response.send_message(
                f"✅ **兌換成功！**\n\n"
                f"你的序號已通過私訊發送給你！\n"
                f"請查看私訊並妥善保管序號\n\n"
                f"💡 使用 `/my_serials` 可隨時查看",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ **兌換成功！**\n\n"
                f"道具：{code_data['item_name']}\n"
                f"序號：`{assigned_serial}`\n\n"
                f"⚠️ 請立即複製並保存你的序號！\n"
                f"💡 建議開啟私訊功能，使用 `/my_serials` 可查看所有序號",
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

@bot.tree.command(name="my_serials", description="查看我已兌換的所有序號")
@require_verified()
async def my_serials(interaction: discord.Interaction):
    init_user(interaction.user.id)
    user_id = str(interaction.user.id)
    user_data = data['users'][user_id]
    
    if 'my_serials' not in user_data or not user_data['my_serials']:
        await interaction.response.send_message(
            "你還沒有兌換過任何序號\n\n"
            "💡 使用 `/redeem` 兌換序號",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🎫 我的序號記錄",
        description="以下是你已兌換的所有序號",
        color=discord.Color.green()
    )
    
    for item in user_data['my_serials']:
        date = datetime.fromisoformat(item['redeemed_at']).strftime('%Y-%m-%d %H:%M')
        embed.add_field(
            name=f"📦 {item['item_name']}",
            value=(
                f"兌換碼：`{item['code']}`\n"
                f"序號：`{item['serial']}`\n"
                f"兌換時間：{date}"
            ),
            inline=False
        )
    
    embed.set_footer(text="⚠️ 請妥善保管你的序號，可以截圖保存")
    
    try:
        await interaction.user.send(embed=embed)
        await interaction.response.send_message(
            "✅ 你的序號記錄已通過私訊發送給你！",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="delete_redeem_code", description="[管理員] 刪除兌換碼")
@app_commands.describe(code="要刪除的兌換碼")
async def delete_redeem_code(interaction: discord.Interaction, code: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ 只有管理員可使用此指令", ephemeral=True)
        return
    
    if code not in data['redemption_codes']:
        await interaction.response.send_message("❌ 此兌換碼不存在！", ephemeral=True)
        return
    
    code_data = data['redemption_codes'][code]
    code_type = "序號池" if code_data['reward_type'] == 'serial' else "積分"
    
    del data['redemption_codes'][code]
    save_data()
    
    await interaction.response.send_message(
        f"✅ **兌換碼已刪除！**\n\n"
        f"代碼：`{code}`\n"
        f"類型：{code_type}",
        ephemeral=True
    )

# ==================== 完整戰鬥系統 ====================
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
    if amount <= 0:
        await interaction.response.send_message("❌ 提升點數必須大於0！", ephemeral=True)
        return
    
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
    
    stat_names = {
        'attack': '攻擊力',
        'defense': '防禦力',
        'hp': '生命值'
    }
    
    embed.add_field(
        name=f"✨ 提升了 {stat_names[stat.value]}",
        value=f"+{amount} → {gear[stat.value]}",
        inline=False
    )
    
    embed.add_field(
        name="💪 當前屬性",
        value=f"攻擊：{gear['attack']}\n防禦：{gear['defense']}\n生命：{gear['hp']}",
        inline=True
    )
    
    embed.add_field(
        name="💰 剩餘積分",
        value=f"遊戲：{user_data['game_points']}\n活動：{user_data['activity_points']}",
        inline=True
    )
    
    total_power = gear['attack'] + gear['defense'] + gear['hp']
    embed.add_field(
        name="⚡ 總戰力",
        value=str(total_power),
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="battle", description="與其他玩家戰鬥")
@require_verified()
@app_commands.describe(opponent="對手")
async def battle(interaction: discord.Interaction, opponent: discord.User):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("❌ 不能與自己戰鬥！", ephemeral=True)
        return
    
    if opponent.bot:
        await interaction.response.send_message("❌ 不能與機器人戰鬥！", ephemeral=True)
        return
    
    init_user(interaction.user.id)
    init_user(opponent.id)
    
    attacker_data = data['users'][str(interaction.user.id)]
    defender_data = data['users'][str(opponent.id)]
    
    attacker_gear = attacker_data['gear']
    defender_gear = defender_data['gear']
    
    # 計算戰力
    attacker_power = attacker_gear['attack'] + attacker_gear['defense'] + attacker_gear['hp']
    defender_power = defender_gear['attack'] + defender_gear['defense'] + defender_gear['hp']
    
    # 隨機骰子
    attacker_roll = random.randint(1, 100)
    defender_roll = random.randint(1, 100)
    
    # 總分
    attacker_total = attacker_power + attacker_roll
    defender_total = defender_power + defender_roll
    
    # 判定勝負
    if attacker_total > defender_total:
        winner = interaction.user
        loser = opponent
        winner_data = attacker_data
        loser_data = defender_data
        winner_power = attacker_power
        loser_power = defender_power
        winner_roll = attacker_roll
        loser_roll = defender_roll
    else:
        winner = opponent
        loser = interaction.user
        winner_data = defender_data
        loser_data = attacker_data
        winner_power = defender_power
        loser_power = attacker_power
        winner_roll = defender_roll
        loser_roll = attacker_roll
    
    # 計算戰利品（失敗者5%的遊戲積分）
    stolen = max(int(loser_data['game_points'] * 0.05), 1)
    stolen = min(stolen, loser_data['game_points'])  # 確保不超過擁有的積分
    
    winner_data['game_points'] += stolen
    loser_data['game_points'] -= stolen
    
    # 更新戰鬥統計
    if 'battle_stats' not in winner_data:
        winner_data['battle_stats'] = {'wins': 0, 'losses': 0, 'total_earned': 0, 'total_lost': 0}
    if 'battle_stats' not in loser_data:
        loser_data['battle_stats'] = {'wins': 0, 'losses': 0, 'total_earned': 0, 'total_lost': 0}
    
    winner_data['battle_stats']['wins'] += 1
    winner_data['battle_stats']['total_earned'] += stolen
    loser_data['battle_stats']['losses'] += 1
    loser_data['battle_stats']['total_lost'] += stolen
    
    save_data()
    
    # 戰鬥結果
    embed = discord.Embed(
        title="⚔️ 戰鬥結果",
        description="激烈的戰鬥結束了！",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="🏆 勝利者",
        value=f"{winner.mention}\n戰力：{winner_power} + 🎲{winner_roll} = **{winner_power + winner_roll}**",
        inline=False
    )
    
    embed.add_field(
        name="💀 失敗者",
        value=f"{loser.mention}\n戰力：{loser_power} + 🎲{loser_roll} = **{loser_power + loser_roll}**",
        inline=False
    )
    
    embed.add_field(
        name="💰 戰利品",
        value=f"{stolen} 遊戲積分",
        inline=True
    )
    
    embed.add_field(
        name="📊 戰後積分",
        value=f"{winner.mention}: {winner_data['game_points']}\n{loser.mention}: {loser_data['game_points']}",
        inline=True
    )
    
    # 戰鬥技巧提示
    if loser_power < winner_power * 0.7:
        embed.add_field(
            name="💡 提示",
            value=f"{loser.mention} 可以使用 `/upgrade_gear` 提升屬性來增強戰力！",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)
    
    # 通知失敗者
    try:
        await loser.send(
            f"⚔️ **戰鬥通知**\n\n"
            f"{winner.mention} 向你發起了挑戰並獲勝！\n"
            f"你失去了 {stolen} 遊戲積分\n"
            f"當前積分：{loser_data['game_points']}\n\n"
            f"💡 使用 `/upgrade_gear` 提升屬性，準備復仇！"
        )
    except:
        pass

# ==================== Help 指令 ====================
@bot.tree.command(name="help", description="查看機器人使用指南")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 機器人使用指南",
        description="以下是所有可用功能的完整說明",
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
            "💡 連續打卡有加成（最高7天）\n"
            "💡 全週打卡有額外獎勵"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 遊戲系統",
        value=(
            "`/game` - 遊戲選單\n"
            "`/minesweeper` - 踩地雷（1.5倍獎勵）\n"
            "`/mineral` - 礦產系統（被動收入）\n"
            "`/mineral_upgrade` - 升級礦場\n"
            "`/mineral_claim` - 領取礦產收益\n"
            "💡 踩地雷支援3種難度\n"
            "💡 礦場每小時產生積分"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ 戰鬥系統",
        value=(
            "`/upgrade_gear` - 提升屬性（攻擊/防禦/生命）\n"
            "`/battle` - 與玩家戰鬥\n"
            "💡 勝利者可獲得對方5%遊戲積分\n"
            "💡 戰力 = 攻擊 + 防禦 + 生命 + 隨機骰子"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💸 轉帳系統",
        value=(
            "`/transfer` - 轉帳積分給其他玩家\n"
            "💡 支援遊戲積分和活動積分\n"
            "💡 手續費5%"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎁 兌換系統",
        value=(
            "`/redeem` - 兌換序號或積分\n"
            "`/my_serials` - 查看我的所有序號\n"
            "💡 支援積分獎勵和道具序號派發\n"
            "💡 序號為20碼格式，會自動私訊給你\n"
            "💡 兌換碼支援每日/每週/每月使用限制"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📊 資料查詢",
        value=(
            "`/profile` - 查看個人資料\n"
            "💡 可查看自己或其他玩家的資料\n"
            "💡 顯示積分、屬性、礦場等級、戰績等"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 管理員指令",
        value=(
            "`/set_verification_channel` - 設置驗證頻道\n"
            "`/set_verified_role` - 設置驗證身分組\n"
            "`/add_redeem_code` - 新增積分兌換碼\n"
            "`/add_serial_code` - 新增序號池（自動生成）\n"
            "`/add_custom_serials` - 新增序號池（手動輸入）\n"
            "`/append_serials` - 補充序號到現有池\n"
            "`/redeem_status` - 查看兌換碼狀態\n"
            "`/list_redeem_codes` - 列出所有兌換碼\n"
            "`/delete_redeem_code` - 刪除兌換碼"
        ),
        inline=False
    )
    
    embed.set_footer(text="💡 所有遊戲功能都已完整實裝！開始遊玩吧！")
    
    await interaction.response.send_message(embed=embed)

# ==================== 啟動機器人 ====================
@bot.event
async def on_ready():
    print(f'✅ 機器人已登入: {bot.user}')
    print(f'📝 序號格式：20碼純文字（無短橫線）')
    print(f'🎮 完整遊戲系統已啟用：')
    print(f'   • 踩地雷（完整版）')
    print(f'   • 礦產系統（完整版）')
    print(f'   • 戰鬥系統（完整版）')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ 成功同步 {len(synced)} 個指令')
    except Exception as e:
        print(f'❌ 指令同步失敗: {e}')

# 請在此處填入你的機器人 TOKEN

bot.run(TOKEN)