# Discord 積分系統機器人

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-blue.svg)](https://github.com/Rapptz/discord.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一個功能完整的 Discord 機器人，包含積分系統、遊戲系統、邀請系統、戰鬥系統等多種互動功能。適合用於社群管理、用戶互動和娛樂。

## 目錄

- [功能特色](#功能特色)
- [安裝說明](#安裝說明)
- [初始設定](#初始設定)
- [指令列表](#指令列表)
- [積分系統說明](#積分系統說明)
- [資料結構](#資料結構)
- [常見問題](#常見問題)
- [安全性建議](#安全性建議)
- [貢獻指南](#貢獻指南)
- [授權許可](#授權許可)

## 功能特色

### 新人驗證系統
- 新成員在指定頻道提交推文截圖
- 管理員點擊反應 ✅ 即可完成驗證
- 自動授予驗證身分組
- 私訊通知用戶驗證成功
- 通過驗證後解鎖所有功能

### 邀請系統
- 每位用戶擁有專屬 8 位邀請碼
- 邀請獎勵：每成功邀請 2 人獲得 10 活動積分
- 可查看邀請記錄和邀請列表
- 防止重複使用和自我邀請
- 邀請者達標時自動通知

### 打卡系統
- 每日打卡獲得遊戲積分和活動積分（各 5 點）
- 連續打卡加成（最高 +7 點，持續 7 天）
- 全週打卡獎勵（額外 20 積分）
- 自動計算打卡連續天數
- 視覺化顯示本週打卡進度

### 遊戲系統
- **踩地雷** - 高風險高回報遊戲
- **賽馬** - 動態賠率競賽
- **輪盤** - 經典賭場遊戲
- **刮刮樂** - 碰運氣小遊戲
- 支援使用遊戲積分或活動積分下注
- 多樣化的遊戲選擇增加互動性

### 轉帳系統
- 玩家間可互相轉帳積分
- 支援遊戲積分和活動積分轉帳
- 5% 手續費機制
- 防止自我轉帳
- 即時通知轉帳結果

### 兌換碼系統
- 管理員可創建兌換碼
- 支援多種有效期設定（永久/每日/每週/每月）
- 可設定使用次數限制（單次/多次/無限）
- 自動記錄兌換歷史
- 防止重複兌換（依有效期而定）
- **序號池派發系統** - 自動分配實體序號
- **20碼序號格式** - 標準化序號管理
- **永久記錄保存** - 玩家可隨時查看已兌換序號

### 戰鬥系統
- 使用積分提升攻擊/防禦/生命值
- 與其他玩家進行 1v1 戰鬥
- 勝利者獲得對方 5% 遊戲積分
- 加入隨機性增加趣味和公平性
- 詳細的戰鬥報告

### 礦產系統
- 被動收入機制
- 可升級礦產等級
- 每日自動產生遊戲積分
- 等級越高收入越多（每級 +10 積分/天）

### 彩票系統
- 累積獎池機制
- 購買彩票參與抽獎
- 中獎者獲得獎池積分
- 定期開獎活動

## 安裝說明

### 環境需求

- **Python**: 3.8 或更高版本
- **Discord.py**: 2.0 或更高版本
- **作業系統**: Windows / Linux / macOS

### 安裝步驟

#### 1. 克隆專案

```bash
git clone https://github.com/yourusername/discord-points-bot.git
cd discord-points-bot
```

#### 2. 安裝依賴套件

```bash
pip install discord.py
```

或使用 requirements.txt（如果有提供）：

```bash
pip install -r requirements.txt
```

#### 3. 創建 Discord 機器人

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 點擊 "New Application" 創建新應用程式
3. 在左側選單選擇 "Bot"
4. 點擊 "Add Bot" 創建機器人
5. 複製機器人 Token（保密！）
6. 啟用以下 Privileged Gateway Intents：
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

#### 4. 邀請機器人到伺服器

1. 在 Developer Portal 選擇 "OAuth2" > "URL Generator"
2. 選擇以下 Scopes：
   - `bot`
   - `applications.commands`
3. 選擇以下 Bot Permissions：
   - Manage Roles
   - Send Messages
   - Embed Links
   - Add Reactions
   - Read Message History
   - Use Slash Commands
4. 複製生成的 URL，在瀏覽器開啟並選擇伺服器

#### 5. 設定機器人 Token

打開 `bot.py`，在檔案最後找到：

```python
TOKEN = 'YOUR_BOT_TOKEN_HERE'
```

替換為你的機器人 Token：

```python
TOKEN = 'your_actual_bot_token_here'
```

**重要**: 不要將 Token 公開到 GitHub！建議使用環境變數：

```python
import os
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
```

然後在終端設定環境變數：

```bash
# Windows
set DISCORD_BOT_TOKEN=your_token_here

# Linux/macOS
export DISCORD_BOT_TOKEN=your_token_here
```

#### 6. 啟動機器人

```bash
python bot.py
```

看到以下訊息表示成功：

```
機器人已登入: YourBotName#1234
成功同步 X 個指令
```

## 初始設定

機器人啟動後，管理員需要進行以下設定：

### 1. 設置驗證頻道

```
/set_verification_channel #任務提交頻道
```

這是新成員提交推文截圖的頻道。

### 2. 設置驗證身分組

```
/set_verified_role @驗證會員
```

通過驗證的成員將自動獲得此身分組。

### 3. 創建兌換碼（可選）

#### 積分兌換碼
```
/add_redeem_code code:WELCOME2024 reward_type:遊戲積分 reward_amount:100 max_uses:50 duration:永久
```

#### 序號池兌換碼（自動生成20碼序號）
```
/add_serial_code code:GIFT2024 item_name:遊戲月卡 quantity:50 duration:永久
```

#### 自訂序號池（手動輸入序號）
```
/add_custom_serials code:STEAM2024 item_name:Steam激活碼 serials:KEY1-AAA-BBB,KEY2-CCC-DDD duration:永久
```

## 指令列表

### 管理員指令

#### 驗證系統
| 指令 | 參數 | 說明 |
|------|------|------|
| `/set_verification_channel` | `channel` | 設置任務提交頻道 |
| `/set_verified_role` | `role` | 設置驗證身分組 |

#### 兌換碼管理
| 指令 | 參數 | 說明 |
|------|------|------|
| `/add_redeem_code` | `code`, `reward_type`, `reward_amount`, `max_uses`, `duration` | 新增積分兌換碼 |
| `/add_serial_code` | `code`, `item_name`, `quantity`, `duration` | 新增序號池（自動生成） |
| `/add_custom_serials` | `code`, `item_name`, `serials`, `duration` | 新增序號池（手動輸入） |
| `/append_serials` | `code`, `quantity`, `custom_serials` | 補充序號到現有序號池 |
| `/redeem_status` | `code` | 查看兌換碼使用狀態 |
| `/list_redeem_codes` | - | 列出所有兌換碼 |
| `/delete_redeem_code` | `code` | 刪除兌換碼 |

### 一般用戶指令

#### 基礎功能

| 指令 | 參數 | 說明 |
|------|------|------|
| `/help` | - | 查看完整使用指南 |
| `/my_invite` | - | 查看我的邀請碼和邀請記錄 |
| `/use_invite` | `code` | 使用別人的邀請碼 |
| `/checkin` | - | 每日打卡領取積分 |

#### 遊戲功能

| 指令 | 參數 | 說明 |
|------|------|------|
| `/game` | - | 開啟遊戲選單 |
| `/minesweeper` | `amount`, `point_type` | 踩地雷遊戲 |
| `/horse_racing` | `amount`, `point_type` | 賽馬遊戲 |
| `/roulette` | `amount`, `point_type` | 輪盤遊戲 |
| `/scratcher` | `amount`, `point_type` | 刮刮樂遊戲 |

#### 交易功能

| 指令 | 參數 | 說明 |
|------|------|------|
| `/transfer` | `user`, `amount`, `point_type` | 轉帳積分給其他玩家 |
| `/redeem` | `code` | 兌換序號或積分 |
| `/my_serials` | - | 查看我已兌換的所有序號 |

#### 戰鬥功能

| 指令 | 參數 | 說明 |
|------|------|------|
| `/upgrade_gear` | `stat`, `amount`, `point_type` | 提升戰鬥屬性 |
| `/battle` | `opponent` | 與其他玩家戰鬥 |

#### 其他功能

| 指令 | 參數 | 說明 |
|------|------|------|
| `/mineral` | - | 查看礦產系統狀態 |
| `/lottery` | - | 彩票系統 |

## 積分系統說明

### 遊戲積分

**用途**：
- 遊戲下注
- 提升戰鬥屬性
- 礦產升級
- 玩家間轉帳

**獲得方式**：
- 每日打卡：5-12 點（含連續加成）
- 遊戲獲勝：依遊戲而定
- 戰鬥勝利：對手 5% 積分
- 礦產收入：依等級而定
- 兌換碼：依設定而定
- 全週打卡：額外 20 點

### 活動積分

**用途**：
- 遊戲下注
- 提升戰鬥屬性
- 玩家間轉帳

**獲得方式**：
- 每日打卡：5-12 點（含連續加成）
- 邀請獎勵：每 2 人 10 點
- 兌換碼：依設定而定
- 全週打卡：額外 20 點

## 序號系統說明

### 序號格式
- **自動生成**：20碼純文字格式（連續20個大寫字母和數字）
- **手動輸入**：支援任意格式

### 序號派發流程
1. 管理員創建序號池（指定數量或手動輸入）
2. 玩家使用 `/redeem` 兌換
3. 系統自動從序號池取出一組未使用的序號
4. 序號通過私訊發送給玩家（更安全）
5. 序號永久保存在玩家記錄中
6. 玩家可隨時使用 `/my_serials` 查看

### 序號池管理
- **創建序號池**：`/add_serial_code`（自動生成）或 `/add_custom_serials`（手動輸入）
- **補充序號**：`/append_serials`（序號快用完時補充）
- **查看狀態**：`/redeem_status`（查看剩餘數量和派發記錄）
- **刪除序號池**：`/delete_redeem_code`

### 使用限制
- **永久（permanent）**：每人只能兌換一次
- **每日（daily）**：每天可兌換一次
- **每週（weekly）**：每週可兌換一次
- **每月（monthly）**：每月可兌換一次

## 資料結構

### bot_data.json

```json
{
  "users": {
    "user_id": {
      "game_points": 0,
      "activity_points": 0,
      "invite_code": "ABC12345",
      "invited_by": "inviter_id",
      "invited_users": ["user1", "user2"],
      "last_checkin": "2024-01-01T12:00:00",
      "checkin_streak": 5,
      "weekly_checkin": [true, true, false, false, false, false, false],
      "gear": {
        "attack": 10,
        "defense": 5,
        "hp": 100
      },
      "mineral_level": 3,
      "mineral_last_claim": "2024-01-01T00:00:00",
      "lottery_tickets": [],
      "redemption_history": {},
      "my_serials": [
        {
          "code": "GIFT2024",
          "item_name": "遊戲月卡",
          "serial": "A3F9K2L8M4N7P1Q6R5T2",
          "redeemed_at": "2024-01-01T12:00:00"
        }
      ]
    }
  },
  "invite_codes": {},
  "redemption_codes": {
    "CODE123": {
      "reward_type": "game",
      "reward_amount": 100,
      "max_uses": 50,
      "current_uses": 10,
      "duration": "permanent",
      "used_by": {
        "user_id": "2024-01-01T12:00:00"
      }
    },
    "GIFT2024": {
      "reward_type": "serial",
      "item_name": "遊戲月卡",
      "max_uses": 50,
      "current_uses": 5,
      "duration": "permanent",
      "used_by": {
        "user_id": "2024-01-01T12:00:00"
      },
      "serial_pool": [
        "A3F9K2L8M4N7P1Q6R5T2",
        "B8G4L9M3N2P7Q6R1S4T9"
      ],
      "serial_assigned": {
        "user_id": "A3F9K2L8M4N7P1Q6R5T2"
      }
    }
  },
  "verification_channel": "channel_id",
  "verified_role": "role_id"
}
```

### 資料備份

**重要**: 定期備份 `bot_data.json` 檔案！

```bash
# 手動備份
cp bot_data.json bot_data.json.backup

# 或使用時間戳記
cp bot_data.json "bot_data_$(date +%Y%m%d_%H%M%S).json"
```

## 常見問題

### Q: 為什麼指令無法使用？

**A**: 請檢查以下幾點：
1. 用戶是否已通過驗證（獲得驗證身分組）
2. 機器人是否有足夠的權限
3. 指令是否已成功同步（查看啟動訊息）
4. 是否在正確的伺服器使用指令

### Q: 如何重置用戶資料？

**A**: 有兩種方式：
1. 手動編輯 `bot_data.json`，刪除或修改特定用戶資料
2. 刪除 `bot_data.json`，重啟機器人（會清空所有資料）

### Q: 機器人離線後資料會遺失嗎？

**A**: 不會。所有資料都儲存在 `bot_data.json` 中，只要檔案不被刪除，資料就會保留。

### Q: 可以修改積分獲得的數量嗎？

**A**: 可以。在程式碼中搜尋相關數值並修改：
- 打卡獎勵：搜尋 `game_reward = 5`
- 邀請獎勵：搜尋 `inviter_data['activity_points'] += 10`
- 戰鬥獎勵：搜尋 `stolen = int(loser_data['game_points'] * 0.05)`

### Q: 如何添加新的遊戲？

**A**: 參考現有遊戲指令的結構，創建新的 `@bot.tree.command`，並在 `GameMenu` 類別中添加對應按鈕。

### Q: 機器人指令沒有出現在 Discord 中？

**A**: 請確認：
1. 機器人已正確啟動（查看終端訊息）
2. 機器人有 `applications.commands` 權限
3. 等待幾分鐘讓 Discord 同步指令
4. 嘗試重新啟動機器人

### Q: 序號系統如何運作？

**A**: 
1. 管理員創建序號池（自動生成或手動輸入）
2. 玩家兌換時，系統自動從池中取出一組序號
3. 序號通過私訊發送（更安全）
4. 每個序號只會派發一次
5. 玩家可使用 `/my_serials` 隨時查看

### Q: 序號用完了怎麼辦？

**A**: 使用 `/append_serials` 指令補充序號到現有序號池。

### Q: 玩家說收不到序號？

**A**: 
1. 請玩家檢查私訊
2. 使用 `/my_serials` 查詢
3. 確認玩家是否開啟私訊功能
4. 管理員可使用 `/redeem_status` 確認序號是否已派發

## 安全性建議

### 1. 保護 Token
**絕對不要**將機器人 Token 公開在 GitHub 或其他公開平台

**應該**使用環境變數或 `.env` 檔案：

```bash
# .env 檔案
DISCORD_BOT_TOKEN=your_token_here
```

```python
# bot.py
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
```

### 2. 定期備份
- 每日自動備份 `bot_data.json`
- 將備份儲存到雲端或外部儲存裝置
- 測試備份的完整性

### 3. 權限管理
- 僅給予機器人必要的權限
- 定期審查管理員名單
- 限制敏感指令的使用

### 4. 監控使用
- 定期檢查兌換碼使用情況
- 監控異常的積分變動
- 記錄重要操作的日誌
- 定期檢查序號池剩餘數量

### 5. 更新維護
- 定期更新 Discord.py 到最新版本
- 關注安全性公告
- 修補已知的漏洞

### 6. 序號安全
- 序號優先通過私訊發送
- 玩家記錄永久保存
- 防止序號重複派發
- 定期審查序號使用記錄

## 貢獻指南

歡迎貢獻！請遵循以下步驟：

1. Fork 此專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

### 貢獻規範

- 遵循現有的程式碼風格
- 添加適當的註解
- 更新相關文檔
- 測試新功能

## 授權許可

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

## 聯絡方式

- **專案維護者**: Your Name
- **Email**: your.email@example.com
- **Discord**: YourDiscord#1234
- **問題回報**: [GitHub Issues](https://github.com/yourusername/discord-points-bot/issues)

## 致謝

- [Discord.py](https://github.com/Rapptz/discord.py) - 優秀的 Discord API 封裝
- [Discord Developer Portal](https://discord.com/developers) - 提供完整的開發文檔

## 更新日誌

### v2.0.0 (2024-02-02)
- 新增完整序號系統
- 自動生成20碼序號功能
- 序號池管理系統
- 玩家序號記錄功能
- 序號補充機制
- 優化安全性（私訊發送）

### v1.0.0 (2024-01-01)
- 初始版本發布
- 新人驗證系統
- 邀請系統
- 打卡系統
- 遊戲系統（踩地雷）
- 轉帳系統
- 兌換碼系統
- 戰鬥系統
- 礦產系統

---

**注意**: 此 README 基於程式碼中的簡化版本。完整的遊戲邏輯（賽馬、輪盤、刮刮樂、彩票等）需要進一步實作。

如有問題或建議，歡迎提交 Issue 或 Pull Request！

**如果這個專案對你有幫助，請給個星星支持一下！**