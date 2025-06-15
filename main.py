# main.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv
from datetime import datetime, date
import asyncio

# 환경 변수 로드
load_dotenv()

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

# 봇 생성
try:
    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or('!'),
        intents=intents,
        help_command=None
    )
except Exception as e:
    print(f"❌ 봇 생성 실패: {e}")
    bot = commands.Bot(
        command_prefix='!',
        intents=intents,
        help_command=None
    )

# 번호표 시스템 데이터
ticket_number = 1
waiting_queue = []
consultation_in_progress = False

# 관리자 설정
NOTIFICATION_CHANNEL_ID= int(os.getenv('NOTIFICATION_CHANNEL_ID'))
ADMIN_CHANNEL_ID = int(os.getenv('ADMIN_CHANNEL_ID'))
CONSULTATION_VOICE_CHANNEL_IDS = {
    "career": int(os.getenv('CAREER_CHANNEL_ID')),
    "study": int(os.getenv('STUDY_VOICE_CHANNEL_ID')),
    "project": int(os.getenv('PROJECT_VOICE_CHANNEL_ID'))
}

# 환경변수 확인
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    exit(1)

# 상담 종류 옵션
counseling_types = [
    {"label": "진로 상담", "value": "career", "emoji": "🎯"},
    {"label": "공부 상담", "value": "study", "emoji": "📚"},
    {"label": "프로젝트 고민", "value": "project", "emoji": "💡"},
    {"label": "기타", "value": "other", "emoji": "💬"}
]

# ========================================
# 게임 기록 시스템 (파일 기반)
# ========================================

RECORDS_FILE = "game_records.json"

def load_game_records():
    """게임 기록을 파일에서 로드"""
    try:
        if os.path.exists(RECORDS_FILE):
            with open(RECORDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 기본 구조 확인 및 보완
                if "tetris" not in data:
                    data["tetris"] = []
                if "rps" not in data:
                    data["rps"] = []
                if "total_games" not in data:
                    data["total_games"] = len(data.get("tetris", [])) + len(data.get("rps", []))
                return data
        else:
            return {
                "tetris": [],
                "rps": [],
                "total_games": 0
            }
    except Exception as e:
        print(f"❌ 게임 기록 로드 실패: {e}")
        return {
            "tetris": [],
            "rps": [],
            "total_games": 0
        }

def save_game_records(records):
    """게임 기록을 파일에 저장"""
    try:
        with open(RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 게임 기록 저장 실패: {e}")
        return False

def add_tetris_record(user_id, username, score, level, lines_cleared, play_time):
    """테트리스 게임 기록 추가"""
    try:
        records = load_game_records()
        
        new_record = {
            "user_id": user_id,
            "username": username,
            "score": score,
            "level": level,
            "lines_cleared": lines_cleared,
            "play_time": play_time,
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat()
        }
        
        records["tetris"].append(new_record)
        records["total_games"] += 1
        
        if save_game_records(records):
            print(f"✅ 테트리스 기록 저장: {username} - {score:,}점")
            return True
        return False
    except Exception as e:
        print(f"❌ 테트리스 기록 추가 실패: {e}")
        return False

def add_rps_record(host_id, host_name, opponent_id, opponent_name, winner_id, host_wins, opponent_wins, rounds_played):
    """가위바위보 게임 기록 추가"""
    try:
        records = load_game_records()
        
        new_record = {
            "host_id": host_id,
            "host_name": host_name,
            "opponent_id": opponent_id,
            "opponent_name": opponent_name,
            "winner_id": winner_id,
            "host_wins": host_wins,
            "opponent_wins": opponent_wins,
            "rounds_played": rounds_played,
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat()
        }
        
        records["rps"].append(new_record)
        records["total_games"] += 1
        
        if save_game_records(records):
            winner_name = host_name if winner_id == host_id else opponent_name if winner_id == opponent_id else "무승부"
            print(f"✅ 가위바위보 기록 저장: {host_name} vs {opponent_name}, 승자: {winner_name}")
            return True
        return False
    except Exception as e:
        print(f"❌ 가위바위보 기록 추가 실패: {e}")
        return False

def get_game_statistics():
    """전체 게임 통계 계산"""
    try:
        records = load_game_records()
        
        # 테트리스 통계
        tetris_stats = {}
        for record in records["tetris"]:
            user_id = record["user_id"]
            username = record["username"]
            score = record["score"]
            
            if user_id not in tetris_stats:
                tetris_stats[user_id] = {
                    "username": username,
                    "games": 0,
                    "best_score": 0,
                    "total_score": 0
                }
            
            tetris_stats[user_id]["games"] += 1
            tetris_stats[user_id]["total_score"] += score
            if score > tetris_stats[user_id]["best_score"]:
                tetris_stats[user_id]["best_score"] = score
        
        # 가위바위보 통계
        rps_stats = {}
        for record in records["rps"]:
            for user_id, user_name in [(record["host_id"], record["host_name"]), 
                                       (record["opponent_id"], record["opponent_name"])]:
                if user_id not in rps_stats:
                    rps_stats[user_id] = {
                        "username": user_name,
                        "games": 0,
                        "wins": 0,
                        "losses": 0,
                        "draws": 0
                    }
                
                rps_stats[user_id]["games"] += 1
                
                if record["winner_id"] == user_id:
                    rps_stats[user_id]["wins"] += 1
                elif record["winner_id"] is None:
                    rps_stats[user_id]["draws"] += 1
                else:
                    rps_stats[user_id]["losses"] += 1
        
        # 승률 계산
        for user_id in rps_stats:
            stats = rps_stats[user_id]
            if stats["games"] > 0:
                stats["win_rate"] = (stats["wins"] / stats["games"]) * 100
            else:
                stats["win_rate"] = 0
        
        return tetris_stats, rps_stats
    except Exception as e:
        print(f"❌ 게임 통계 계산 실패: {e}")
        return {}, {}

def get_today_statistics():
    """오늘 게임 통계 계산"""
    try:
        records = load_game_records()
        today = date.today().isoformat()
        
        # 오늘 테트리스 게임
        today_tetris = [r for r in records["tetris"] if r.get("date") == today]
        
        # 오늘 가위바위보 게임
        today_rps = [r for r in records["rps"] if r.get("date") == today]
        
        # 테트리스 통계
        tetris_stats = {}
        for record in today_tetris:
            user_id = record["user_id"]
            username = record["username"]
            score = record["score"]
            
            if user_id not in tetris_stats:
                tetris_stats[user_id] = {
                    "username": username,
                    "games": 0,
                    "best_score": 0,
                    "total_score": 0
                }
            
            tetris_stats[user_id]["games"] += 1
            tetris_stats[user_id]["total_score"] += score
            if score > tetris_stats[user_id]["best_score"]:
                tetris_stats[user_id]["best_score"] = score
        
        # 가위바위보 통계
        rps_stats = {}
        for record in today_rps:
            for user_id, user_name in [(record["host_id"], record["host_name"]), 
                                       (record["opponent_id"], record["opponent_name"])]:
                if user_id not in rps_stats:
                    rps_stats[user_id] = {
                        "username": user_name,
                        "games": 0,
                        "wins": 0,
                        "losses": 0,
                        "draws": 0
                    }
                
                rps_stats[user_id]["games"] += 1
                
                if record["winner_id"] == user_id:
                    rps_stats[user_id]["wins"] += 1
                elif record["winner_id"] is None:
                    rps_stats[user_id]["draws"] += 1
                else:
                    rps_stats[user_id]["losses"] += 1
        
        # 승률 계산
        for user_id in rps_stats:
            stats = rps_stats[user_id]
            if stats["games"] > 0:
                stats["win_rate"] = (stats["wins"] / stats["games"]) * 100
            else:
                stats["win_rate"] = 0
        
        return tetris_stats, rps_stats, len(today_tetris), len(today_rps)
    except Exception as e:
        print(f"❌ 오늘 게임 통계 계산 실패: {e}")
        return {}, {}, 0, 0

# 게임 기록 시스템 초기화
print("📊 게임 기록 시스템 초기화 중...")
game_records = load_game_records()
print(f"✅ 기존 기록 로드 완료: 테트리스 {len(game_records['tetris'])}개, 가위바위보 {len(game_records['rps'])}개")

# ========================================
# 음성 채널 관리 함수들
# ========================================

async def disconnect_user_from_voice(user_id: int, interaction: discord.Interaction = None):
    """특정 사용자를 음성 채널에서 연결 끊기시키는 함수"""
    try:
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        print(f"🔇 음성 연결 끊기 시도: {user_id}")
        
        member = None
        
        if interaction and interaction.guild:
            member = interaction.guild.get_member(user_id)
            print(f"🔍 Interaction guild에서 검색: {member is not None}")
        
        if not member and CONSULTATION_VOICE_CHANNEL_IDS:
            for consultation_type, channel_id in CONSULTATION_VOICE_CHANNEL_IDS.items():
                consultation_channel = bot.get_channel(channel_id)
                if consultation_channel and consultation_channel.guild:
                    member = consultation_channel.guild.get_member(user_id)
                    if member:
                        print(f"🔍 상담 채널 guild에서 검색: {member is not None}")
                        break
        
        if not member:
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    print(f"🔍 {guild.name}에서 사용자 발견")
                    break
        
        if not member:
            print(f"⚠️ 연결 끊기: 사용자를 찾을 수 없음 {user_id}")
            return False
        
        if not member.voice or not member.voice.channel:
            print(f"ℹ️ {member.display_name}님이 음성 채널에 접속하지 않았습니다.")
            return True
        
        current_channel = member.voice.channel.name
        print(f"🎤 현재 음성 채널: {current_channel}")
        
        await member.move_to(None)
        print(f"✅ {member.display_name}님을 음성 채널에서 연결 끊기 완료")
        
        return True
        
    except discord.Forbidden:
        print(f"❌ {member.display_name if member else user_id}님을 음성 채널에서 연결 끊을 권한이 없습니다.")
        return False
    except discord.HTTPException as e:
        print(f"❌ 음성 채널 연결 끊기 중 오류 발생: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        return False

async def move_user_to_consultation_channel(user_id: int, consultation_type: str, interaction: discord.Interaction = None):
    """특정 사용자를 상담용 음성 채널로 이동시키는 함수"""
    if not CONSULTATION_VOICE_CHANNEL_IDS:
        error_msg = "❌ 상담용 음성 채널이 설정되지 않았습니다. 상담 채널 환경변수를 확인해주세요."
        print(error_msg)
        if interaction:
            await interaction.followup.send(error_msg, ephemeral=True)
        return False
    
    try:
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        print(f"🔍 사용자 검색 중: {user_id}")
        
        consultation_channel = None
        
        # consultation_type이 정확히 일치하는 키를 찾아 해당 채널 ID로 이동
        print(consultation_type)
        channel_id = CONSULTATION_VOICE_CHANNEL_IDS.get(consultation_type)
        
        if not channel_id:
            # "other" 타입의 경우 기본적으로 career 채널 사용
            if consultation_type == "other":
                channel_id = CONSULTATION_VOICE_CHANNEL_IDS.get("career")
            
            if not channel_id:
                error_msg = f"❌ '{consultation_type}' 상담용 음성 채널을 찾을 수 없습니다: {CONSULTATION_VOICE_CHANNEL_IDS}"
                print(error_msg)
                if interaction:
                    await interaction.followup.send(error_msg, ephemeral=True)
                return False
        
        consultation_channel = bot.get_channel(channel_id)
        print(consultation_channel)
        if not consultation_channel:
            error_msg = f"❌ 상담용 음성 채널을 찾을 수 없습니다: {channel_id}"
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        member = None
        
        if interaction and interaction.guild:
            member = interaction.guild.get_member(user_id)
            print(f"🔍 Interaction guild에서 검색: {member is not None}")
        
        if not member and consultation_channel.guild:
            member = consultation_channel.guild.get_member(user_id)
            print(f"🔍 상담 채널 guild에서 검색: {member is not None}")
        
        if not member:
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    print(f"🔍 {guild.name}에서 사용자 발견")
                    break
        
        if not member:
            guilds_info = [f"{guild.name}({len(guild.members)}명)" for guild in bot.guilds]
            error_msg = f"❌ 사용자를 찾을 수 없습니다: {user_id}\n서버 목록: {', '.join(guilds_info)}"
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        print(f"✅ 사용자 발견: {member.display_name} ({member.id})")
        
        if not member.voice:
            error_msg = f"❌ {member.display_name}님이 음성 채널에 접속하지 않았습니다."
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        # 이미 상담용 음성 채널에 있는지 확인 (수정된 부분)
        current_channel_id = member.voice.channel.id
        all_consultation_channels = list(CONSULTATION_VOICE_CHANNEL_IDS.values())  # 정수값들의 리스트로 변환
        
        if current_channel_id in all_consultation_channels:
            success_msg = f"✅ {member.display_name}님이 이미 상담용 음성 채널에 있습니다."
            print(success_msg)
            if interaction:
                await interaction.followup.send(success_msg, ephemeral=True)
            return True
        
        await member.move_to(consultation_channel)
        success_msg = f"✅ {member.display_name}님을 상담용 음성 채널로 이동시켰습니다."
        print(success_msg)
        if interaction:
            await interaction.followup.send(success_msg, ephemeral=True)
        return True
        
    except discord.Forbidden:
        error_msg = "❌ 사용자를 음성 채널로 이동시킬 권한이 없습니다."
        print(error_msg)
        if interaction:
            await interaction.followup.send(error_msg, ephemeral=True)
        return False
    except discord.HTTPException as e:
        error_msg = f"❌ 음성 채널 이동 중 오류 발생: {e}"
        print(error_msg)
        if interaction:
            await interaction.followup.send(error_msg, ephemeral=True)
        return False
    except Exception as e:
        error_msg = f"❌ 예상치 못한 오류 발생: {e}"
        print(error_msg)
        if interaction:
            await interaction.followup.send(error_msg, ephemeral=True)
        return False

# ========================================
# 상담 시스템 관련 함수들
# ========================================

async def send_admin_channel_notification(ticket_info):
    """관리자 채널에 새로운 번호표 알림 전송"""
    if not ADMIN_CHANNEL_ID: 
        return
    
    try:
        embed = discord.Embed(
            title="🆕 새로운 상담 신청",
            color=0x00ff88
        )
        embed.add_field(name="번호", value=f"**{ticket_info['number']}번**", inline=True)
        embed.add_field(name="상담 종류", value=get_counseling_type_label(ticket_info['type']), inline=True)
        embed.add_field(name="신청자", value=ticket_info['username'], inline=True)
        embed.add_field(name="신청 시간", value=f"<t:{int(ticket_info['timestamp'].timestamp())}:T>", inline=False)
        
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            await admin_channel.send(embed=embed)
    
    except Exception as e:
        print(f"❌ 관리자 채널 알림 전송 실패: {e}")

async def update_admin_panel():
    """관리자 패널 업데이트"""
    if not ADMIN_CHANNEL_ID: 
        return
    
    try:
        admin_channel = bot.get_channel(int(ADMIN_CHANNEL_ID))
        if not admin_channel:
            return
        
        # 기존 관리자 패널 메시지 찾기
        async for message in admin_channel.history(limit=50):
            if (message.author == bot.user and 
                message.embeds and 
                "관리자 패널" in message.embeds[0].title):
                await message.delete()
                break
        
        # 새로운 관리자 패널 생성
        if waiting_queue:
            queue_text = []
            for i, ticket in enumerate(waiting_queue[:10]):
                if i == 0 and consultation_in_progress:
                    status = "🔴 상담 중"
                elif i == 0:
                    status = "🟢 다음 순서"
                else:
                    status = "🟡 대기 중"
                
                queue_text.append(
                    f"{status} **{ticket['number']}번** | "
                    f"{get_counseling_type_label(ticket['type'])} | "
                    f"{ticket['username']}"
                )
            
            embed = discord.Embed(
                title="🎛️ 관리자 패널",
                description="\n".join(queue_text),
                color=0x5865f2
            )

            if waiting_queue:
                if consultation_in_progress:
                    if len(waiting_queue) > 1:
                        next_number = f"{waiting_queue[1]['number']}번"
                    else:
                        next_number = "없음"
                else:
                    next_number = f"{waiting_queue[0]['number']}번"
                status_text = f"총 대기: **{len(waiting_queue) - 1 if consultation_in_progress else len(waiting_queue)}명**\n다음 번호: **{next_number}**"
            else:
                status_text = f"총 대기: **0명**\n다음 번호: **없음**"
            if consultation_in_progress and waiting_queue:
                status_text += f"\n🔴 현재 **{waiting_queue[0]['number']}번** 상담 진행 중"
            
            embed.add_field(
                name="📊 현황",
                value=status_text,
                inline=False
            )
            
            # 상담 채널 정보 표시
            voice_info_parts = []
            for consultation_type, channel_id in CONSULTATION_VOICE_CHANNEL_IDS.items():
                consultation_channel = bot.get_channel(channel_id)
                if consultation_channel:
                    type_label = get_counseling_type_label(consultation_type)
                    voice_info_parts.append(f"{type_label}: {consultation_channel.mention}")
            
            if voice_info_parts:
                embed.add_field(name="🔊 음성 채널", value="\n".join(voice_info_parts), inline=False)

            embed.timestamp = datetime.now()
            embed.set_footer(text="버튼을 클릭하여 대기열을 관리하세요")
        else:
            embed = discord.Embed(
                title="🎛️ 관리자 패널",
                description="현재 대기 중인 상담이 없습니다.",
                color=0x95a5a6
            )
            embed.add_field(
                name="📊 현황",
                value=f"총 대기: **0명**",
                inline=False
            )
            
            # 상담 채널 정보 표시
            voice_info_parts = []
            for consultation_type, channel_id in CONSULTATION_VOICE_CHANNEL_IDS.items():
                consultation_channel = bot.get_channel(channel_id)
                if consultation_channel:
                    type_label = get_counseling_type_label(consultation_type)
                    voice_info_parts.append(f"{type_label}: {consultation_channel.mention}")
            
            if voice_info_parts:
                embed.add_field(name="🔊 음성 채널", value="\n".join(voice_info_parts), inline=False)
            
            embed.timestamp = datetime.now()
        
        view = AdminPanelView(consultation_in_progress)
        await admin_channel.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ 관리자 패널 업데이트 실패: {e}")

def get_counseling_type_label(type_value):
    """상담 종류 값에 해당하는 라벨 반환"""
    type_info = next((ct for ct in counseling_types if ct["value"] == type_value), None)
    return f"{type_info['emoji']} {type_info['label']}" if type_info else "❓ 알 수 없음"

async def check_admin_permission(interaction: discord.Interaction):
    """관리자 권한 체크"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 기능입니다.", ephemeral=True)
        return False
    return True

# ========================================
# Discord UI 클래스들
# ========================================

class AdminPanelView(discord.ui.View):
    def __init__(self, consultation_in_progress=False):
        super().__init__(timeout=None)
        
        if not consultation_in_progress and waiting_queue:
            self.add_item(StartConsultationButton())
        
        if consultation_in_progress and waiting_queue:
            self.add_item(CompleteConsultationButton())

        self.add_item(RefreshQueueButton())
        self.add_item(CompleteSpecificButton())
        self.add_item(MoveUserButton())
        self.add_item(DisconnectUserButton())

class StartConsultationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='상담 시작', style=discord.ButtonStyle.success, emoji='▶️')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 대기 중인 상담이 없습니다.", ephemeral=True)
            return
        
        consultation_in_progress = True
        next_ticket = waiting_queue[0]
        
        embed = discord.Embed(
            title="▶️ 상담 시작",
            description=f"**{next_ticket['number']}번** 상담을 시작합니다.",
            color=0x00ff00
        )
        embed.add_field(name="상담 종류", value=get_counseling_type_label(next_ticket['type']), inline=True)
        embed.add_field(name="상담자", value=next_ticket['username'], inline=True)
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)
        
        await move_user_to_consultation_channel(next_ticket['user_id'], next_ticket['type'], interaction)
        
        await update_admin_panel()

class CompleteConsultationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='상담 완료', style=discord.ButtonStyle.danger, emoji='✅')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 완료할 상담이 없습니다.", ephemeral=True)
            return
        
        completed_ticket = waiting_queue.pop(0)
        consultation_in_progress = False
        
        await disconnect_user_from_voice(completed_ticket['user_id'], interaction)
        
        embed = discord.Embed(
            title="✅ 상담 완료",
            description=f"**{completed_ticket['number']}번** 상담이 완료되었습니다.",
            color=0xff0000
        )
        embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
        embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
        embed.add_field(name="남은 대기", value=f"{len(waiting_queue)}명", inline=True)
        embed.add_field(name="🔇 음성 연결", value="자동으로 연결 끊기 완료", inline=False)
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)
        await update_admin_panel()

class RefreshQueueButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='대기열 새로고침', style=discord.ButtonStyle.secondary, emoji='🔄')
    
    async def callback(self, interaction: discord.Interaction):
        if not await check_admin_permission(interaction):
            return
        
        await interaction.response.send_message("🔄 대기열을 새로고침했습니다.", ephemeral=True)
        await update_admin_panel()

class CompleteSpecificButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='특정 번호 완료', style=discord.ButtonStyle.secondary, emoji='🎯')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 대기 중인 상담이 없습니다.", ephemeral=True)
            return
        
        modal = CompleteSpecificModal()
        await interaction.response.send_modal(modal)

class MoveUserButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='사용자 이동', style=discord.ButtonStyle.secondary, emoji='🔊')
    
    async def callback(self, interaction: discord.Interaction):
        if not await check_admin_permission(interaction):
            return
        
        modal = MoveUserModal()
        await interaction.response.send_modal(modal)

class DisconnectUserButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='음성 연결 끊기', style=discord.ButtonStyle.secondary, emoji='🔇')
    
    async def callback(self, interaction: discord.Interaction):
        if not await check_admin_permission(interaction):
            return
        
        modal = DisconnectUserModal()
        await interaction.response.send_modal(modal)

class CompleteSpecificModal(discord.ui.Modal, title='특정 번호 완료'):
    ticket_number = discord.ui.TextInput(
        label='완료할 번호표 번호',
        placeholder='예: 5',
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        try:
            number = int(self.ticket_number.value)
            ticket_index = next((i for i, ticket in enumerate(waiting_queue) if ticket['number'] == number), -1)
            
            if ticket_index == -1:
                await interaction.response.send_message(f"❌ {number}번 번호표를 찾을 수 없습니다.", ephemeral=True)
                return
            
            if ticket_index == 0:
                consultation_in_progress = False
            
            completed_ticket = waiting_queue.pop(ticket_index)
            
            await disconnect_user_from_voice(completed_ticket['user_id'], interaction)
            
            embed = discord.Embed(
                title="✅ 특정 번호 완료",
                description=f"**{completed_ticket['number']}번** 상담이 완료되었습니다.",
                color=0xff0000
            )
            embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
            embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
            embed.add_field(name="🔇 음성 연결", value="자동으로 연결 끊기 완료", inline=False)
            embed.timestamp = datetime.now()
            
            await interaction.response.send_message(embed=embed)
            await update_admin_panel()
            
        except ValueError:
            await interaction.response.send_message("❌ 올바른 숫자를 입력해주세요.", ephemeral=True)

class MoveUserModal(discord.ui.Modal, title='사용자 음성 채널 이동'):
    user_input = discord.ui.TextInput(
        label='이동할 사용자',
        placeholder='사용자명, 사용자 ID, 멘션, 번호표 번호 (예: 홍길동, 123456789, @사용자, 5)',
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.user_input.value.strip()
        user_id = None
        consultation_type = "career"  # 기본값
        target_ticket = None
        target_username = None
        
        try:
            print(f"🔍 사용자명으로 검색: '{user_input}'")
            
            # 현재 서버에서 사용자명으로 멤버 찾기
            member = None
            
            # 1. 정확한 표시 이름 매치
            for guild_member in interaction.guild.members:
                if guild_member.display_name.lower() == user_input.lower():
                    member = guild_member
                    print(f"🔍 정확한 표시명 매치: {member.display_name}")
                    break
            
            # 2. 정확한 매치가 없으면 부분 매치 시도
            if not member:
                for guild_member in interaction.guild.members:
                    if user_input.lower() in guild_member.display_name.lower():
                        member = guild_member
                        print(f"🔍 부분 표시명 매치: {member.display_name}")
                        break
            
            # 3. 사용자명으로도 찾기 시도
            if not member:
                for guild_member in interaction.guild.members:
                    if guild_member.name.lower() == user_input.lower():
                        member = guild_member
                        print(f"🔍 사용자명 매치: {member.name}")
                        break
            
            if not member:
                await interaction.response.send_message(f"❌ '{user_input}' 사용자를 찾을 수 없습니다.", ephemeral=True)
                return
            
            user_id = member.id
            target_username = member.display_name
            print(f"🔍 사용자명에서 찾은 ID: {user_id}, 표시명: {target_username}")
            
            if user_id:
                # 번호표가 아직 확인되지 않은 경우 (사용자 ID, 멘션, 또는 사용자명으로 입력한 경우)
                if not target_ticket:
                    # 해당 사용자의 번호표가 있는지 확인
                    user_ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
                    if user_ticket:
                        consultation_type = user_ticket['type']
                        target_ticket = user_ticket
                        if not target_username:
                            target_username = user_ticket['username']
                        print(f"🔍 사용자 ID {user_id}의 번호표 발견, 상담 타입: {consultation_type}")
                    else:
                        # 사용자명이 없으면 멤버 정보에서 가져오기
                        if not target_username:
                            member = interaction.guild.get_member(user_id)
                            target_username = member.display_name if member else f"ID: {user_id}"
                        print(f"🔍 사용자 ID {user_id}의 번호표 없음, 기본 타입 사용: {consultation_type}")
                
                print(f"🔍 최종 사용자 ID: {user_id}, 상담 타입: {consultation_type}, 사용자명: {target_username}")
                
                # 상담 타입에 대한 설명 추가
                type_description = get_counseling_type_label(consultation_type)
                await interaction.response.send_message(
                    f"🔊 {target_username}님을 {type_description} 음성 채널로 이동 중...", 
                    ephemeral=True
                )
                
                # 상담 타입에 맞는 채널로 이동
                success = await move_user_to_consultation_channel(user_id, consultation_type, interaction)
                
                if success:
                    if target_ticket:
                        # 번호표가 있는 경우
                        embed = discord.Embed(
                            title="🔊 사용자 이동 완료",
                            description=f"**{target_ticket['number']}번** {target_username}님을 {type_description} 음성 채널로 이동했습니다.",
                            color=0x00ff00
                        )
                        embed.add_field(name="상담 종류", value=type_description, inline=True)
                        embed.add_field(name="번호표", value=f"{target_ticket['number']}번", inline=True)
                    else:
                        # 번호표가 없는 경우
                        embed = discord.Embed(
                            title="🔊 사용자 이동 완료",
                            description=f"{target_username}님을 {type_description} 음성 채널로 이동했습니다.",
                            color=0x00ff00
                        )
                        embed.add_field(name="상담 종류", value=type_description, inline=True)
                        embed.add_field(name="번호표", value="없음 (기본 채널 사용)", inline=True)
                    
                    embed.timestamp = datetime.now()
                    await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message("❌ 사용자를 찾을 수 없습니다.", ephemeral=True)
        except ValueError as e:
            print(f"❌ ValueError: {e}")
            await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요.", ephemeral=True)
        except Exception as e:
            print(f"❌ Exception: {e}")
            await interaction.response.send_message(f"❌ 오류가 발생했습니다: {e}", ephemeral=True)

class DisconnectUserModal(discord.ui.Modal, title='사용자 음성 연결 끊기'):
    user_input = discord.ui.TextInput(
        label='연결 끊을 사용자',
        placeholder='사용자명, 사용자 ID, 멘션, 번호표 번호 (예: 홍길동, 123456789, @사용자, 5)',
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.user_input.value.strip()
        user_id = None
        target_ticket = None
        target_username = None
        
        try:
            print(f"🔇 음성 연결 끊기 요청: '{user_input}'")
                
            # 현재 서버에서 사용자명으로 멤버 찾기
            member = None
            
            # 1. 정확한 표시 이름 매치
            for guild_member in interaction.guild.members:
                if guild_member.display_name.lower() == user_input.lower():
                    member = guild_member
                    print(f"🔍 정확한 표시명 매치: {member.display_name}")
                    break
            
            # 2. 정확한 매치가 없으면 부분 매치 시도
            if not member:
                for guild_member in interaction.guild.members:
                    if user_input.lower() in guild_member.display_name.lower():
                        member = guild_member
                        print(f"🔍 부분 표시명 매치: {member.display_name}")
                        break
            
            # 3. 사용자명으로도 찾기 시도
            if not member:
                for guild_member in interaction.guild.members:
                    if guild_member.name.lower() == user_input.lower():
                        member = guild_member
                        print(f"🔍 사용자명 매치: {member.name}")
                        break
            
            if not member:
                await interaction.response.send_message(f"❌ '{user_input}' 사용자를 찾을 수 없습니다.", ephemeral=True)
                return
            
            user_id = member.id
            target_username = member.display_name
            print(f"🔍 사용자명에서 찾은 ID: {user_id}, 표시명: {target_username}")
            
            if user_id:
                # 번호표가 아직 확인되지 않은 경우 (사용자 ID, 멘션, 또는 사용자명으로 입력한 경우)
                if not target_ticket:
                    # 해당 사용자의 번호표가 있는지 확인
                    user_ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
                    if user_ticket:
                        target_ticket = user_ticket
                        if not target_username:
                            target_username = user_ticket['username']
                        print(f"🔍 사용자 ID {user_id}의 번호표 발견")
                    else:
                        # 사용자명이 없으면 멤버 정보에서 가져오기
                        if not target_username:
                            member = interaction.guild.get_member(user_id)
                            target_username = member.display_name if member else f"ID: {user_id}"
                        print(f"🔍 사용자 ID {user_id}의 번호표 없음")
                
                print(f"🔇 최종 연결 끊기 대상 ID: {user_id}, 사용자명: {target_username}")
                
                await interaction.response.send_message(
                    f"🔇 {target_username}님을 음성 채널에서 연결 끊는 중...", 
                    ephemeral=True
                )
                
                success = await disconnect_user_from_voice(user_id, interaction)
                
                if success:
                    if target_ticket:
                        # 번호표가 있는 경우
                        embed = discord.Embed(
                            title="🔇 음성 연결 끊기 완료",
                            description=f"**{target_ticket['number']}번** {target_username}님의 음성 연결을 끊었습니다.",
                            color=0xff9900
                        )
                        embed.add_field(name="상담 종류", value=get_counseling_type_label(target_ticket['type']), inline=True)
                        embed.add_field(name="번호표", value=f"{target_ticket['number']}번", inline=True)
                    else:
                        # 번호표가 없는 경우
                        embed = discord.Embed(
                            title="🔇 음성 연결 끊기 완료",
                            description=f"{target_username}님의 음성 연결을 끊었습니다.",
                            color=0xff9900
                        )
                        embed.add_field(name="번호표", value="없음", inline=True)
                    
                    embed.timestamp = datetime.now()
                    await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message("❌ 사용자를 찾을 수 없습니다.", ephemeral=True)
                
        except ValueError as e:
            print(f"❌ ValueError: {e}")
            await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요.", ephemeral=True)
        except Exception as e:
            print(f"❌ Exception: {e}")
            await interaction.response.send_message(f"❌ 오류가 발생했습니다: {e}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='번호표 발급받기', style=discord.ButtonStyle.primary, emoji='🎫')
    async def issue_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        existing_ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == interaction.user.id), None)
        if existing_ticket:
            await interaction.response.send_message(
                f"❌ 이미 **{existing_ticket['number']}번** 번호표를 발급받으셨습니다!\n"
                f"상담 종류: {get_counseling_type_label(existing_ticket['type'])}", 
                ephemeral=True
            )
            return
        
        view = CounselingTypeSelect()
        await interaction.response.send_message("📝 상담 종류를 선택해주세요:", view=view, ephemeral=True)

class CounselingTypeSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.select(
        placeholder="상담 종류를 선택해주세요",
        options=[
            discord.SelectOption(
                label=counseling_type["label"],
                value=counseling_type["value"],
                emoji=counseling_type["emoji"]
            ) for counseling_type in counseling_types
        ]
    )
    async def select_counseling_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        global ticket_number
        
        selected_type = select.values[0]
        current_number = ticket_number
        ticket_number += 1
        
        new_ticket = {
            'number': current_number,
            'user_id': interaction.user.id,
            'username': interaction.user.display_name,
            'type': selected_type,
            'timestamp': datetime.now()
        }
        
        waiting_queue.append(new_ticket)
        
        asyncio.create_task(send_admin_channel_notification(new_ticket))
        asyncio.create_task(update_admin_panel())
        
        embed = discord.Embed(
            title="✅ 번호표 발급 완료!",
            color=0x00ff00
        )
        embed.add_field(name="🎫 번호", value=f"**{current_number}번**", inline=True)
        embed.add_field(name="📋 상담 종류", value=get_counseling_type_label(selected_type), inline=True)
        embed.add_field(name="👤 신청자", value=interaction.user.display_name, inline=True)
        embed.add_field(name="⏰ 발급 시간", value=f"<t:{int(datetime.now().timestamp())}:T>", inline=False)
        embed.set_footer(text="대기열 확인은 /대기열 명령어를 사용하세요")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        public_embed = discord.Embed(
            title="🔔 새로운 상담 신청",
            description=f"**{current_number}번** 번호표가 발급되었습니다.",
            color=0xffff00
        )
        public_embed.add_field(name="상담 종류", value=get_counseling_type_label(selected_type), inline=True)
        public_embed.add_field(name="현재 대기", value=f"{len(waiting_queue)}명", inline=True)
        
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            await admin_channel.send(embed=public_embed)

# ========================================
# 게임 모듈 import (기록 시스템 초기화 후)
# ========================================
from tetris_game import start_tetris_game
from rock_paper_scissors_game import start_rps_game

print("🎮 게임 모듈 import 완료!")

# ========================================
# 이벤트 핸들러
# ========================================

@bot.event
async def on_ready():
    print(f'✅ {bot.user} 봇이 준비되었습니다!')
    print(f'🤖 봇 ID: {bot.user.id}')
    print(f'🏠 참여 서버 수: {len(bot.guilds)}')
    
    for guild in bot.guilds:
        print(f'   📍 {guild.name} (ID: {guild.id}, 멤버: {guild.member_count}명)')
    
    print("\n🔧 환경변수 체크:")
    print(f"   • DISCORD_TOKEN: {'✅ 설정됨' if DISCORD_TOKEN else '❌ 없음'}")
    print(f"   • ADMIN_CHANNEL_ID: {'✅ 설정됨' if ADMIN_CHANNEL_ID else '⚠️ 설정되지 않음'}")
    
    # 상담 채널별 체크
    for consultation_type, channel_id in CONSULTATION_VOICE_CHANNEL_IDS.items():
        print(f"   • {consultation_type.upper()}_CHANNEL_ID: {'✅ 설정됨' if channel_id else '⚠️ 설정되지 않음'}")
    
    print(f'\n🔧 활성화된 인텐트:')
    print(f'   • members: {bot.intents.members}')
    print(f'   • guilds: {bot.intents.guilds}')
    print(f'   • voice_states: {bot.intents.voice_states}')
    print(f'   • message_content: {bot.intents.message_content}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)}개의 슬래시 커맨드가 동기화되었습니다!')
        
        print("📋 동기화된 커맨드:")
        for cmd in synced:
            print(f"   • /{cmd.name}: {cmd.description}")
            
    except Exception as e:
        print(f'❌ 커맨드 동기화 실패: {e}')
        print("❌ 봇이 서버에 추가되어 있고 applications.commands 권한이 있는지 확인하세요.")
    
    print(f'\n🚀 봇이 성공적으로 시작되었습니다!')
    print(f'📝 사용 가능한 주요 명령어:')
    print(f'   • /번호표 - 상담 번호표 발급')
    print(f'   • /테트리스 - 테트리스 게임 시작') 
    print(f'   • /가위바위보 - 삼세판 가위바위보 게임 시작')
    print(f'   • /게임통계 - 전체 게임 순위 및 통계')
    print(f'   • /오늘게임통계 - 오늘 게임 통계')
    print(f'   • /대기열 - 대기열 확인')
    print(f'   • /관리자패널 - 관리자 패널 (관리자만)')
    print(f'\n📊 게임 기록 시스템이 활성화되었습니다!')
    print(f'   - 모든 게임이 {RECORDS_FILE} 파일에 자동 저장됩니다')
    print(f'   - /게임통계로 전체 순위를 확인하세요')
    print(f'   - /오늘게임통계로 오늘의 게임 현황을 확인하세요')
    
    try:
        records = load_game_records()
        print("=" * 50)
        print("🔍 게임 기록 시스템 초기 상태")
        print("=" * 50)
        print(f"📊 총 게임 수: {records['total_games']}")
        print(f"🎯 테트리스 게임: {len(records['tetris'])}개")
        print(f"✂️ 가위바위보 게임: {len(records['rps'])}개")
        print(f"✅ 게임 기록 시스템이 정상적으로 초기화되었습니다!")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 게임 기록 시스템 상태 확인 실패: {e}")

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 핸들링"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ 봇에게 필요한 권한이 없습니다.")
    else:
        print(f'❌ 예상치 못한 에러 발생: {error}')
        print(f'❌ 에러 타입: {type(error)}')
        
@bot.event
async def on_error(event, *args, **kwargs):
    """일반 에러 핸들링"""
    print(f'❌ 이벤트 에러 발생: {event}')
    import traceback
    traceback.print_exc()

# ========================================
# 슬래시 커맨드들
# ========================================

@bot.tree.command(name="번호표", description="진로상담 번호표를 발급받습니다")
async def ticket_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 진로상담 번호표 발급",
        description="아래 버튼을 클릭하여 번호표를 발급받으세요!",
        color=0x0099ff
    )
    embed.add_field(
        name="📋 이용 안내",
        value="• 번호표 발급 후 상담 종류를 선택해주세요\n• 순서대로 상담이 진행됩니다\n• 대기 시간은 상황에 따라 달라질 수 있습니다\n• 상담 시작 시 자동으로 음성 채널로 이동됩니다",
        inline=False
    )
    embed.timestamp = datetime.now()
    
    view = TicketView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="대기열", description="현재 대기 중인 상담 목록을 확인합니다")
async def queue_command(interaction: discord.Interaction):
    if not waiting_queue:
        embed = discord.Embed(
            title="📋 대기열 현황",
            description="현재 대기 중인 상담이 없습니다.",
            color=0x808080
        )
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)
        return
    
    queue_description = []
    for ticket in waiting_queue:
        type_label = get_counseling_type_label(ticket['type'])
        time_ago = f"<t:{int(ticket['timestamp'].timestamp())}:R>"
        queue_description.append(f"**{ticket['number']}번** | {type_label} | {ticket['username']} {time_ago}")
    
    embed = discord.Embed(
        title="📋 진로상담 대기열 현황",
        description="\n".join(queue_description),
        color=0xff9900
    )
    embed.add_field(
        name="📊 통계",
        value=f"• 총 대기: **{len(waiting_queue)}명**\n• 다음 순서: **{waiting_queue[0]['number']}번**",
        inline=False
    )
    embed.timestamp = datetime.now()
    embed.set_footer(text="상담 완료 시 /완료 명령어를 사용하세요")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="완료", description="상담을 완료처리 합니다")
@app_commands.describe(번호="완료할 번호표 번호")
async def complete_command(interaction: discord.Interaction, 번호: int):
    global consultation_in_progress
    
    ticket_index = next((i for i, ticket in enumerate(waiting_queue) if ticket['number'] == 번호), -1)
    
    if ticket_index == -1:
        await interaction.response.send_message(f"❌ {번호}번 번호표를 찾을 수 없습니다.", ephemeral=True)
        return
    
    if ticket_index == 0:
        consultation_in_progress = False
    
    completed_ticket = waiting_queue.pop(ticket_index)
    
    await disconnect_user_from_voice(completed_ticket['user_id'], interaction)
    
    embed = discord.Embed(
        title="✅ 상담 완료",
        color=0x00ff00
    )
    embed.add_field(name="번호표", value=f"{completed_ticket['number']}번", inline=True)
    embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
    embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
    embed.add_field(name="🔇 음성 연결", value="자동으로 연결 끊기 완료", inline=False)
    embed.timestamp = datetime.now()
    
    await interaction.response.send_message(embed=embed)
    await update_admin_panel()

@bot.tree.command(name="초기화", description="대기열을 초기화합니다 (관리자 전용)")
async def reset_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 대기열을 초기화할 수 있습니다.", ephemeral=True)
        return
    
    global ticket_number, consultation_in_progress
    previous_count = len(waiting_queue)
    waiting_queue.clear()
    ticket_number = 1
    consultation_in_progress = False
    
    embed = discord.Embed(
        title="🔄 대기열 초기화",
        description=f"{previous_count}개의 대기 중인 상담이 초기화되었습니다.",
        color=0xff0000
    )
    embed.timestamp = datetime.now()
    
    await interaction.response.send_message(embed=embed)
    await update_admin_panel()

@bot.tree.command(name="관리자패널", description="관리자 패널을 생성합니다 (관리자 전용)")
async def admin_panel_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    await interaction.response.send_message("🎛️ 관리자 패널을 생성했습니다.", ephemeral=True)
    await update_admin_panel()

@bot.tree.command(name="이동", description="특정 사용자를 상담용 음성 채널로 이동시킵니다 (관리자 전용)")
@app_commands.describe(
    사용자명="이동시킬 사용자명 (디스코드 표시 이름)",
    번호="번호표 번호 (선택사항)"
)
async def move_user_command(interaction: discord.Interaction, 사용자명: str = None, 번호: int = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    user_id = None
    consultation_type = "career"  # 기본값
    target_user = None
    
    # 번호표 번호로 검색하는 경우
    if 번호:
        ticket = next((ticket for ticket in waiting_queue if ticket['number'] == 번호), None)
        if not ticket:
            await interaction.response.send_message(f"❌ {번호}번 번호표를 찾을 수 없습니다.", ephemeral=True)
            return
        user_id = ticket['user_id']
        consultation_type = ticket['type']  # 번호표의 상담 타입 사용
        target_user = ticket['username']
        
    # 사용자명으로 검색하는 경우
    elif 사용자명:
        # 현재 서버에서 사용자명으로 멤버 찾기
        member = None
        
        # 정확한 표시 이름 매치
        for guild_member in interaction.guild.members:
            if guild_member.display_name.lower() == 사용자명.lower():
                member = guild_member
                break
        
        # 정확한 매치가 없으면 부분 매치 시도
        if not member:
            for guild_member in interaction.guild.members:
                if 사용자명.lower() in guild_member.display_name.lower():
                    member = guild_member
                    break
        
        # 사용자명으로도 찾기 시도
        if not member:
            for guild_member in interaction.guild.members:
                if guild_member.name.lower() == 사용자명.lower():
                    member = guild_member
                    break
        
        if not member:
            await interaction.response.send_message(f"❌ '{사용자명}' 사용자를 찾을 수 없습니다.", ephemeral=True)
            return
        
        user_id = member.id
        target_user = member.display_name
        
        # 해당 사용자의 번호표가 있는지 확인하여 상담 타입 결정
        user_ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
        if user_ticket:
            consultation_type = user_ticket['type']
        else:
            # 번호표가 없으면 기본 타입 사용하고 안내 메시지 추가
            consultation_type = "career"
    
    else:
        await interaction.response.send_message("❌ 사용자명 또는 번호표 번호를 지정해주세요.", ephemeral=True)
        return
    
    await interaction.response.send_message(f"🔊 {target_user}님을 {get_counseling_type_label(consultation_type)} 음성 채널로 이동 중...", ephemeral=True)
    
    # 상담 타입에 맞는 채널로 이동
    success = await move_user_to_consultation_channel(user_id, consultation_type, interaction)
    
    if success:
        # 번호표가 있는 경우
        if 번호:
            ticket = next((ticket for ticket in waiting_queue if ticket['number'] == 번호), None)
            embed = discord.Embed(
                title="🔊 사용자 이동 완료",
                description=f"**{ticket['number']}번** {ticket['username']}님을 {get_counseling_type_label(consultation_type)} 음성 채널로 이동했습니다.",
                color=0x00ff00
            )
        # 사용자명으로 이동한 경우
        else:
            user_ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
            if user_ticket:
                embed = discord.Embed(
                    title="🔊 사용자 이동 완료",
                    description=f"**{user_ticket['number']}번** {target_user}님을 {get_counseling_type_label(consultation_type)} 음성 채널로 이동했습니다.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="🔊 사용자 이동 완료",
                    description=f"{target_user}님을 {get_counseling_type_label(consultation_type)} 음성 채널로 이동했습니다.\n(번호표 없음 - 기본 진로상담 채널 사용)",
                    color=0x00ff00
                )
        
        embed.add_field(name="상담 타입", value=get_counseling_type_label(consultation_type), inline=True)
        embed.timestamp = datetime.now()
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="연결끊기", description="특정 사용자를 음성 채널에서 연결 끊습니다 (관리자 전용)")
@app_commands.describe(
    사용자="연결을 끊을 사용자",
    번호="번호표 번호 (선택사항)"
)
async def disconnect_user_command(interaction: discord.Interaction, 사용자: discord.Member = None, 번호: int = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    user_id = None
    
    if 번호:
        ticket = next((ticket for ticket in waiting_queue if ticket['number'] == 번호), None)
        if not ticket:
            await interaction.response.send_message(f"❌ {번호}번 번호표를 찾을 수 없습니다.", ephemeral=True)
            return
        user_id = ticket['user_id']
    elif 사용자:
        user_id = 사용자.id
    else:
        await interaction.response.send_message("❌ 사용자 또는 번호표 번호를 지정해주세요.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔇 사용자를 음성 채널에서 연결 끊는 중...", ephemeral=True)
    success = await disconnect_user_from_voice(user_id, interaction)
    
    if success and 번호:
        ticket = next((ticket for ticket in waiting_queue if ticket['number'] == 번호), None)
        if ticket:
            embed = discord.Embed(
                title="🔇 음성 연결 끊기 완료",
                description=f"**{ticket['number']}번** {ticket['username']}님의 음성 연결을 끊었습니다.",
                color=0xff9900
            )
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="공지", description="공지사항을 전송합니다 (관리자 전용)")
@app_commands.describe(
    메시지="전송할 메시지 내용"
)
async def announcement_command(interaction: discord.Interaction, 메시지: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    try:
        notification = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        embed = discord.Embed(
            title="📢 공지사항",
            description=메시지,
            color=0xff6b35
        )
        embed.set_footer(text=f"관리자: {interaction.user.display_name}")
        embed.timestamp = datetime.now()
        
        await notification.send(embed=embed)
        await interaction.response.send_message(f"✅ {notification.mention}에 공지사항을 전송했습니다.", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {notification.mention}에 메시지를 보낼 권한이 없습니다.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 메시지 전송 실패: {e}", ephemeral=True)

@bot.tree.command(name="디버그", description="대기열 사용자 정보를 확인합니다 (관리자 전용)")
async def debug_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    if not waiting_queue:
        await interaction.response.send_message("❌ 대기열이 비어있습니다.", ephemeral=True)
        return
    
    debug_info = []
    debug_info.append(f"**🔍 디버그 정보**")
    debug_info.append(f"총 대기: {len(waiting_queue)}명")
    debug_info.append(f"봇이 참여한 서버: {len(bot.guilds)}개")
    debug_info.append("")
    
    for i, ticket in enumerate(waiting_queue[:5], 1):
        user_id = ticket['user_id']
        username = ticket['username']
        
        member = None
        found_guild = None
        
        member = interaction.guild.get_member(user_id)
        if member:
            found_guild = interaction.guild.name
        else:
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    found_guild = guild.name
                    break
        
        status = "✅ 발견됨" if member else "❌ 없음"
        voice_status = "🎤 음성채널 접속" if member and member.voice else "🔇 음성채널 미접속"
        
        debug_info.append(f"**{ticket['number']}번** {username}")
        debug_info.append(f"├ ID: `{user_id}`")
        debug_info.append(f"├ 상태: {status}")
        if found_guild:
            debug_info.append(f"├ 서버: {found_guild}")
        if member:
            debug_info.append(f"└ 음성: {voice_status}")
        else:
            debug_info.append(f"└ 음성: 확인 불가")
        debug_info.append("")
    
    embed = discord.Embed(
        title="🛠️ 대기열 디버그 정보",
        description="\n".join(debug_info),
        color=0xff9900
    )
    embed.timestamp = datetime.now()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================================
# 게임 관련 명령어들
# ========================================

@bot.tree.command(name="테트리스", description="테트리스 게임을 시작합니다")
async def tetris_command(interaction: discord.Interaction):
    """테트리스 게임 시작 명령어"""
    await start_tetris_game(interaction, record_callback=add_tetris_record)

@bot.tree.command(name="가위바위보", description="삼세판 가위바위보 게임을 시작합니다")
async def rps_command(interaction: discord.Interaction):
    """가위바위보 게임 시작 명령어"""
    await start_rps_game(interaction, record_callback=add_rps_record)

@bot.tree.command(name="게임통계", description="전체 게임 통계 및 순위를 확인합니다")
async def game_statistics_command(interaction: discord.Interaction):
    """전체 게임 통계 명령어"""
    try:
        tetris_stats, rps_stats = get_game_statistics()
        
        embed = discord.Embed(
            title="🏆 전체 게임 통계 및 순위",
            color=0xffd700
        )
        
        # 테트리스 순위 (최고 점수 기준)
        if tetris_stats:
            tetris_ranking = sorted(tetris_stats.items(), key=lambda x: x[1]['best_score'], reverse=True)
            tetris_text = []
            for i, (user_id, stats) in enumerate(tetris_ranking[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}위"
                tetris_text.append(f"{medal} {stats['username']} - {stats['best_score']:,}점 ({stats['games']}게임)")
            
            embed.add_field(
                name="🎯 테트리스 순위 (최고 점수)",
                value="\n".join(tetris_text) if tetris_text else "기록 없음",
                inline=False
            )
        
        # 가위바위보 순위 (승률 기준, 최소 3게임 이상)
        if rps_stats:
            qualified_rps = {k: v for k, v in rps_stats.items() if v['games'] >= 3}
            if qualified_rps:
                rps_ranking = sorted(qualified_rps.items(), key=lambda x: x[1]['win_rate'], reverse=True)
                rps_text = []
                for i, (user_id, stats) in enumerate(rps_ranking[:10], 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}위"
                    rps_text.append(f"{medal} {stats['username']} - {stats['win_rate']:.1f}% ({stats['wins']}승 {stats['losses']}패 {stats['draws']}무)")
                
                embed.add_field(
                    name="✂️ 가위바위보 순위 (승률, 3게임 이상)",
                    value="\n".join(rps_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✂️ 가위바위보 순위 (승률, 3게임 이상)",
                    value="3게임 이상 플레이한 사용자가 없습니다.",
                    inline=False
                )
        
        # 전체 통계
        records = load_game_records()
        total_tetris = len(records['tetris'])
        total_rps = len(records['rps'])
        total_games = records['total_games']
        
        embed.add_field(
            name="📊 전체 통계",
            value=f"총 게임 수: **{total_games}게임**\n테트리스: **{total_tetris}게임**\n가위바위보: **{total_rps}게임**",
            inline=False
        )
        
        embed.timestamp = datetime.now()
        embed.set_footer(text="오늘의 게임 통계는 /오늘게임통계 명령어를 사용하세요")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ 게임 통계 조회 실패: {e}")
        await interaction.response.send_message("❌ 게임 통계를 불러오는 중 오류가 발생했습니다.", ephemeral=True)

@bot.tree.command(name="오늘게임통계", description="오늘의 게임 통계를 확인합니다")
async def today_statistics_command(interaction: discord.Interaction):
    """오늘 게임 통계 명령어"""
    try:
        tetris_stats, rps_stats, tetris_count, rps_count = get_today_statistics()
        
        embed = discord.Embed(
            title=f"📅 오늘의 게임 통계 ({date.today().strftime('%Y-%m-%d')})",
            color=0x00ff88
        )
        
        # 오늘 테트리스 순위
        if tetris_stats:
            tetris_ranking = sorted(tetris_stats.items(), key=lambda x: x[1]['best_score'], reverse=True)
            tetris_text = []
            for i, (user_id, stats) in enumerate(tetris_ranking[:5], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}위"
                tetris_text.append(f"{medal} {stats['username']} - {stats['best_score']:,}점 ({stats['games']}게임)")
            
            embed.add_field(
                name="🎯 오늘 테트리스 순위",
                value="\n".join(tetris_text),
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 오늘 테트리스 순위",
                value="오늘 플레이한 테트리스 게임이 없습니다.",
                inline=False
            )
        
        # 오늘 가위바위보 순위
        if rps_stats:
            qualified_rps = {k: v for k, v in rps_stats.items() if v['games'] >= 2}  # 오늘은 2게임 이상으로 기준 완화
            if qualified_rps:
                rps_ranking = sorted(qualified_rps.items(), key=lambda x: x[1]['win_rate'], reverse=True)
                rps_text = []
                for i, (user_id, stats) in enumerate(rps_ranking[:5], 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}위"
                    rps_text.append(f"{medal} {stats['username']} - {stats['win_rate']:.1f}% ({stats['wins']}승 {stats['losses']}패 {stats['draws']}무)")
                
                embed.add_field(
                    name="✂️ 오늘 가위바위보 순위 (2게임 이상)",
                    value="\n".join(rps_text),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✂️ 오늘 가위바위보 순위",
                    value="오늘 2게임 이상 플레이한 사용자가 없습니다.",
                    inline=False
                )
        else:
            embed.add_field(
                name="✂️ 오늘 가위바위보 순위",
                value="오늘 플레이한 가위바위보 게임이 없습니다.",
                inline=False
            )
        
        # 오늘 전체 통계
        total_today = tetris_count + rps_count
        embed.add_field(
            name="📊 오늘 통계",
            value=f"총 게임 수: **{total_today}게임**\n테트리스: **{tetris_count}게임**\n가위바위보: **{rps_count}게임**",
            inline=False
        )
        
        embed.timestamp = datetime.now()
        embed.set_footer(text="전체 통계는 /게임통계 명령어를 사용하세요")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ 오늘 게임 통계 조회 실패: {e}")
        await interaction.response.send_message("❌ 오늘 게임 통계를 불러오는 중 오류가 발생했습니다.", ephemeral=True)

@bot.tree.command(name="기록초기화", description="게임 기록을 초기화합니다 (관리자 전용)")
async def reset_records_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    try:
        records = load_game_records()
        previous_tetris = len(records['tetris'])
        previous_rps = len(records['rps'])
        previous_total = records['total_games']
        
        # 기록 초기화
        new_records = {
            "tetris": [],
            "rps": [],
            "total_games": 0
        }
        
        if save_game_records(new_records):
            embed = discord.Embed(
                title="🔄 게임 기록 초기화 완료",
                description="모든 게임 기록이 초기화되었습니다.",
                color=0xff0000
            )
            embed.add_field(
                name="🗑️ 삭제된 기록",
                value=f"테트리스: **{previous_tetris}개**\n가위바위보: **{previous_rps}개**\n총합: **{previous_total}개**",
                inline=False
            )
            embed.timestamp = datetime.now()
            embed.set_footer(text="기록이 완전히 삭제되었습니다. 복구할 수 없습니다.")
            
            await interaction.response.send_message(embed=embed)
            print(f"🔄 관리자 {interaction.user.display_name}이 게임 기록을 초기화했습니다.")
        else:
            await interaction.response.send_message("❌ 게임 기록 초기화에 실패했습니다.", ephemeral=True)
            
    except Exception as e:
        print(f"❌ 게임 기록 초기화 실패: {e}")
        await interaction.response.send_message("❌ 게임 기록 초기화 중 오류가 발생했습니다.", ephemeral=True)

# 봇 실행
if __name__ == "__main__":
    try:
        print("🚀 봇을 시작합니다...")
        print(f"🔑 토큰 확인: {'✅ 설정됨' if DISCORD_TOKEN else '❌ 없음'}")
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ 잘못된 토큰입니다. DISCORD_TOKEN을 확인해주세요.")
    except discord.PrivilegedIntentsRequired:
        print("❌ 권한이 필요한 인텐트가 활성화되지 않았습니다.")
        print("❌ Discord Developer Portal에서 다음을 활성화해주세요:")
        print("   - SERVER MEMBERS INTENT")
        print("   - MESSAGE CONTENT INTENT")
    except Exception as e:
        print(f"❌ 봇 실행 중 오류 발생: {e}")
        print("❌ 가능한 해결방법:")
        print("   1. .env 파일에 올바른 DISCORD_TOKEN 설정")
        print("   2. 봇 권한 확인")
        print("   3. 인터넷 연결 확인")