# main.py
import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio

# 환경 변수 로드
load_dotenv()

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # 길드 관련 인텐트 추가
intents.voice_states = True  # 음성 상태 인텐트 추가
intents.members = True  # 멤버 인텐트 추가 (중요!)
bot = commands.Bot(command_prefix='!', intents=intents)

# 번호표 시스템 데이터
ticket_number = 1
waiting_queue = []
consultation_in_progress = False  # 현재 상담 진행 중 여부

# 관리자 설정 (환경변수에서 가져오기)
ADMIN_CHANNEL_ID = os.getenv('ADMIN_CHANNEL_ID')
CONSULTATION_VOICE_CHANNEL_ID = os.getenv('CONSULTATION_VOICE_CHANNEL_ID')  # 상담용 음성 채널 ID

# 상담 종류 옵션
counseling_types = [
    {"label": "진로 상담", "value": "career", "emoji": "🎯"},
    {"label": "공부 상담", "value": "study", "emoji": "📚"},
    {"label": "프로젝트 고민", "value": "project", "emoji": "💡"},
    {"label": "기타", "value": "other", "emoji": "💬"}
]

async def disconnect_user_from_voice(user_id: int, interaction: discord.Interaction = None):
    """특정 사용자를 음성 채널에서 연결 끊기시키는 함수"""
    try:
        # user_id 타입 확인 및 변환
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        print(f"🔇 음성 연결 끊기 시도: {user_id}")
        
        # 사용자 가져오기 - 개선된 로직
        member = None
        
        # 1. interaction에서 guild 가져오기 (최우선)
        if interaction and interaction.guild:
            member = interaction.guild.get_member(user_id)
            print(f"🔍 Interaction guild에서 검색: {member is not None}")
        
        # 2. 못 찾으면 상담 채널이 있는 guild에서 검색
        if not member and CONSULTATION_VOICE_CHANNEL_ID:
            consultation_channel = bot.get_channel(int(CONSULTATION_VOICE_CHANNEL_ID))
            if consultation_channel and consultation_channel.guild:
                member = consultation_channel.guild.get_member(user_id)
                print(f"🔍 상담 채널 guild에서 검색: {member is not None}")
        
        # 3. 그래도 못 찾으면 모든 guild에서 검색
        if not member:
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    print(f"🔍 {guild.name}에서 사용자 발견")
                    break
        
        if not member:
            print(f"⚠️ 연결 끊기: 사용자를 찾을 수 없음 {user_id}")
            return False
        
        # 사용자가 음성 채널에 있는지 확인
        if not member.voice or not member.voice.channel:
            print(f"ℹ️ {member.display_name}님이 음성 채널에 접속하지 않았습니다.")
            return True  # 이미 연결이 끊어진 상태이므로 성공으로 간주
        
        current_channel = member.voice.channel.name
        print(f"🎤 현재 음성 채널: {current_channel}")
        
        # 음성 채널에서 연결 끊기 (move_to(None))
        await member.move_to(None)
        print(f"✅ {member.display_name}님을 음성 채널에서 연결 끊기 완료")
        
        # 성공 메시지 (상담 완료 시에는 너무 많은 메시지를 보내지 않도록 로그만)
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

async def move_user_to_consultation_channel(user_id: int, interaction: discord.Interaction = None):
    """특정 사용자를 상담용 음성 채널로 이동시키는 함수"""
    if not CONSULTATION_VOICE_CHANNEL_ID:
        error_msg = "❌ 상담용 음성 채널이 설정되지 않았습니다. CONSULTATION_VOICE_CHANNEL_ID 환경변수를 확인해주세요."
        print(error_msg)
        if interaction:
            await interaction.followup.send(error_msg, ephemeral=True)
        return False
    
    try:
        # user_id 타입 확인 및 변환
        if isinstance(user_id, str):
            user_id = int(user_id)
        
        print(f"🔍 사용자 검색 중: {user_id}")
        
        # 음성 채널 가져오기
        consultation_channel = bot.get_channel(int(CONSULTATION_VOICE_CHANNEL_ID))
        if not consultation_channel:
            error_msg = f"❌ 상담용 음성 채널을 찾을 수 없습니다: {CONSULTATION_VOICE_CHANNEL_ID}"
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        # 사용자 가져오기 - 개선된 로직
        member = None
        
        # 1. interaction에서 guild 가져오기 (최우선)
        if interaction and interaction.guild:
            member = interaction.guild.get_member(user_id)
            print(f"🔍 Interaction guild에서 검색: {member is not None}")
        
        # 2. 못 찾으면 consultation_channel이 있는 guild에서 검색
        if not member and consultation_channel.guild:
            member = consultation_channel.guild.get_member(user_id)
            print(f"🔍 상담 채널 guild에서 검색: {member is not None}")
        
        # 3. 그래도 못 찾으면 모든 guild에서 검색
        if not member:
            for guild in bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    print(f"🔍 {guild.name}에서 사용자 발견")
                    break
        
        if not member:
            # 추가 정보와 함께 오류 메시지
            guilds_info = [f"{guild.name}({len(guild.members)}명)" for guild in bot.guilds]
            error_msg = f"❌ 사용자를 찾을 수 없습니다: {user_id}\n서버 목록: {', '.join(guilds_info)}"
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        print(f"✅ 사용자 발견: {member.display_name} ({member.id})")
        
        # 사용자가 음성 채널에 있는지 확인
        if not member.voice:
            error_msg = f"❌ {member.display_name}님이 음성 채널에 접속하지 않았습니다."
            print(error_msg)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            return False
        
        # 이미 상담용 채널에 있는지 확인
        if member.voice.channel and member.voice.channel.id == int(CONSULTATION_VOICE_CHANNEL_ID):
            success_msg = f"✅ {member.display_name}님이 이미 상담용 음성 채널에 있습니다."
            print(success_msg)
            if interaction:
                await interaction.followup.send(success_msg, ephemeral=True)
            return True
        
        # 음성 채널로 이동
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

async def send_admin_channel_notification(ticket_info):
    """관리자 채널에 새로운 번호표 알림 전송"""
    if not ADMIN_CHANNEL_ID:
        return
    
    try:
        admin_channel = bot.get_channel(int(ADMIN_CHANNEL_ID))
        if not admin_channel:
            print(f"❌ 관리자 채널을 찾을 수 없습니다: {ADMIN_CHANNEL_ID}")
            return
        
        embed = discord.Embed(
            title="🆕 새로운 상담 신청",
            color=0x00ff88
        )
        embed.add_field(name="번호", value=f"**{ticket_info['number']}번**", inline=True)
        embed.add_field(name="상담 종류", value=get_counseling_type_label(ticket_info['type']), inline=True)
        embed.add_field(name="신청자", value=ticket_info['username'], inline=True)
        embed.add_field(name="신청 시간", value=f"<t:{int(ticket_info['timestamp'].timestamp())}:T>", inline=False)
        
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
        
        # 기존 관리자 패널 메시지 찾기 (봇이 보낸 메시지 중에서)
        async for message in admin_channel.history(limit=50):
            if (message.author == bot.user and 
                message.embeds and 
                "관리자 패널" in message.embeds[0].title):
                await message.delete()
                break
        
        # 새로운 관리자 패널 생성
        if waiting_queue:
            queue_text = []
            for i, ticket in enumerate(waiting_queue[:10]):  # 최대 10개만 표시
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
            
            # 음성 채널 정보 추가
            if CONSULTATION_VOICE_CHANNEL_ID:
                consultation_channel = bot.get_channel(int(CONSULTATION_VOICE_CHANNEL_ID))
                if consultation_channel:
                    voice_info = f"🎤 상담 채널: {consultation_channel.mention}"
                    embed.add_field(name="🔊 음성 설정", value=voice_info, inline=False)
            
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
            
            # 음성 채널 정보 추가
            if CONSULTATION_VOICE_CHANNEL_ID:
                consultation_channel = bot.get_channel(int(CONSULTATION_VOICE_CHANNEL_ID))
                if consultation_channel:
                    voice_info = f"🎤 상담 채널: {consultation_channel.mention}"
                    embed.add_field(name="🔊 음성 설정", value=voice_info, inline=False)
            
            embed.timestamp = datetime.now()
        
        view = AdminPanelView(consultation_in_progress)
        await admin_channel.send(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ 관리자 패널 업데이트 실패: {e}")

class AdminPanelView(discord.ui.View):
    def __init__(self, consultation_in_progress=False):
        super().__init__(timeout=None)
        
        # 상담 진행 중이 아닐 때만 "다음 상담 시작" 버튼 추가
        if not consultation_in_progress and waiting_queue:
            self.add_item(StartConsultationButton())
        
        if consultation_in_progress and waiting_queue:
            self.add_item(CompleteConsultationButton())

        # 항상 표시되는 버튼들
        self.add_item(RefreshQueueButton())
        self.add_item(CompleteSpecificButton())
        self.add_item(MoveUserButton())  # 사용자 이동 버튼 추가
        self.add_item(DisconnectUserButton())  # 사용자 연결 끊기 버튼 추가

class StartConsultationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='상담 시작', style=discord.ButtonStyle.success, emoji='▶️')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 대기 중인 상담이 없습니다.", ephemeral=True)
            return
        
        # 상담 시작
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
        
        # 상담자를 음성 채널로 이동 시도
        await move_user_to_consultation_channel(next_ticket['user_id'], interaction)
        
        await update_admin_panel()

class CompleteConsultationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='상담 완료', style=discord.ButtonStyle.danger, emoji='✅')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 완료할 상담이 없습니다.", ephemeral=True)
            return
        
        completed_ticket = waiting_queue.pop(0)  # 첫 번째(진행 중인) 상담 완료
        consultation_in_progress = False  # 상담 완료 후 상태 리셋
        
        # 상담 완료된 사용자를 음성 채널에서 연결 끊기
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
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        await interaction.response.send_message("🔄 대기열을 새로고침했습니다.", ephemeral=True)
        await update_admin_panel()

class CompleteSpecificButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='특정 번호 완료', style=discord.ButtonStyle.secondary, emoji='🎯')
    
    async def callback(self, interaction: discord.Interaction):
        global consultation_in_progress
        
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        if not waiting_queue:
            await interaction.response.send_message("❌ 대기 중인 상담이 없습니다.", ephemeral=True)
            return
        
        # 번호 선택 모달 표시
        modal = CompleteSpecificModal()
        await interaction.response.send_modal(modal)

class DisconnectUserButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='음성 연결 끊기', style=discord.ButtonStyle.secondary, emoji='🔇')
    
    async def callback(self, interaction: discord.Interaction):
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        # 사용자 연결 끊기 모달 표시
        modal = DisconnectUserModal()
        await interaction.response.send_modal(modal)

class DisconnectUserModal(discord.ui.Modal, title='사용자 음성 연결 끊기'):
    user_input = discord.ui.TextInput(
        label='연결 끊을 사용자',
        placeholder='사용자 ID 또는 멘션 또는 번호표 번호 (예: 123456789, @사용자, 5)',
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.user_input.value.strip()
        user_id = None
        
        try:
            print(f"🔇 음성 연결 끊기 요청: '{user_input}'")
            
            # 멘션 형태인지 확인 (<@123456789> 또는 <@!123456789>)
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id_str = user_input[2:-1]
                if user_id_str.startswith('!'):
                    user_id_str = user_id_str[1:]
                user_id = int(user_id_str)
                print(f"🔍 멘션에서 추출한 ID: {user_id}")
            
            # 숫자인지 확인 (사용자 ID 또는 번호표 번호)
            elif user_input.isdigit():
                number = int(user_input)
                print(f"🔍 숫자 입력: {number}")
                
                # 번호표 번호로 먼저 검색
                ticket = next((ticket for ticket in waiting_queue if ticket['number'] == number), None)
                if ticket:
                    user_id = ticket['user_id']
                    print(f"🔍 번호표 {number}번에서 찾은 사용자 ID: {user_id}")
                else:
                    # 번호표에 없으면 사용자 ID로 간주
                    user_id = number
                    print(f"🔍 사용자 ID로 간주: {user_id}")
            
            else:
                await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요. (사용자 ID, 멘션, 또는 번호표 번호)", ephemeral=True)
                return
            
            if user_id:
                print(f"🔇 최종 연결 끊기 대상 ID: {user_id}")
                await interaction.response.send_message(f"🔇 사용자를 음성 채널에서 연결 끊는 중... (ID: {user_id})", ephemeral=True)
                success = await disconnect_user_from_voice(user_id, interaction)
                
                if success:
                    # 번호표 정보가 있으면 추가 정보 표시
                    ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
                    if ticket:
                        embed = discord.Embed(
                            title="🔇 음성 연결 끊기 완료",
                            description=f"**{ticket['number']}번** {ticket['username']}님의 음성 연결을 끊었습니다.",
                            color=0xff9900
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="🔇 음성 연결 끊기 완료",
                            description=f"사용자 ID {user_id}의 음성 연결을 끊었습니다.",
                            color=0xff9900
                        )
                        await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message("❌ 사용자를 찾을 수 없습니다.", ephemeral=True)
                
        except ValueError as e:
            print(f"❌ ValueError: {e}")
            await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요.", ephemeral=True)
        except Exception as e:
            print(f"❌ Exception: {e}")
            await interaction.response.send_message(f"❌ 오류가 발생했습니다: {e}", ephemeral=True)

class MoveUserButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='사용자 이동', style=discord.ButtonStyle.secondary, emoji='🔊')
    
    async def callback(self, interaction: discord.Interaction):
        # 관리자 권한 체크
        if not await check_admin_permission(interaction):
            return
        
        # 사용자 이동 모달 표시
        modal = MoveUserModal()
        await interaction.response.send_modal(modal)

class MoveUserModal(discord.ui.Modal, title='사용자 음성 채널 이동'):
    user_input = discord.ui.TextInput(
        label='이동할 사용자',
        placeholder='사용자 ID 또는 멘션 또는 번호표 번호 (예: 123456789, @사용자, 5)',
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.user_input.value.strip()
        user_id = None
        
        try:
            print(f"🔍 사용자 입력 처리: '{user_input}'")
            
            # 멘션 형태인지 확인 (<@123456789> 또는 <@!123456789>)
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id_str = user_input[2:-1]
                if user_id_str.startswith('!'):
                    user_id_str = user_id_str[1:]
                user_id = int(user_id_str)
                print(f"🔍 멘션에서 추출한 ID: {user_id}")
            
            # 숫자인지 확인 (사용자 ID 또는 번호표 번호)
            elif user_input.isdigit():
                number = int(user_input)
                print(f"🔍 숫자 입력: {number}")
                
                # 번호표 번호로 먼저 검색
                ticket = next((ticket for ticket in waiting_queue if ticket['number'] == number), None)
                if ticket:
                    user_id = ticket['user_id']
                    print(f"🔍 번호표 {number}번에서 찾은 사용자 ID: {user_id}")
                else:
                    # 번호표에 없으면 사용자 ID로 간주
                    user_id = number
                    print(f"🔍 사용자 ID로 간주: {user_id}")
            
            else:
                await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요. (사용자 ID, 멘션, 또는 번호표 번호)", ephemeral=True)
                return
            
            if user_id:
                print(f"🔍 최종 사용자 ID: {user_id}")
                await interaction.response.send_message(f"🔊 사용자를 음성 채널로 이동 중... (ID: {user_id})", ephemeral=True)
                success = await move_user_to_consultation_channel(user_id, interaction)
                
                if success:
                    # 번호표 정보가 있으면 추가 정보 표시
                    ticket = next((ticket for ticket in waiting_queue if ticket['user_id'] == user_id), None)
                    if ticket:
                        embed = discord.Embed(
                            title="🔊 사용자 이동 완료",
                            description=f"**{ticket['number']}번** {ticket['username']}님을 상담용 음성 채널로 이동했습니다.",
                            color=0x00ff00
                        )
                        await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message("❌ 사용자를 찾을 수 없습니다.", ephemeral=True)
                
        except ValueError as e:
            print(f"❌ ValueError: {e}")
            await interaction.response.send_message("❌ 올바른 형식으로 입력해주세요.", ephemeral=True)
        except Exception as e:
            print(f"❌ Exception: {e}")
            await interaction.response.send_message(f"❌ 오류가 발생했습니다: {e}", ephemeral=True)

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
            
            # 첫 번째 항목(현재 상담 중)을 완료하는 경우 상담 상태 리셋
            if ticket_index == 0:
                consultation_in_progress = False
            
            completed_ticket = waiting_queue.pop(ticket_index)
            
            # 상담 완료된 사용자를 음성 채널에서 연결 끊기
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

async def check_admin_permission(interaction: discord.Interaction):
    """관리자 권한 체크"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 기능입니다.", ephemeral=True)
        return False
    return True

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
        
        # 알림 전송 (비동기로)
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
        
        await interaction.followup.send(embed=public_embed)

def get_counseling_type_label(type_value):
    """상담 종류 값에 해당하는 라벨 반환"""
    type_info = next((ct for ct in counseling_types if ct["value"] == type_value), None)
    return f"{type_info['emoji']} {type_info['label']}" if type_info else "❓ 알 수 없음"

@bot.event
async def on_ready():
    print(f'✅ {bot.user} 봇이 준비되었습니다!')
    print(f'🤖 봇 ID: {bot.user.id}')
    print(f'🏠 참여 서버 수: {len(bot.guilds)}')
    
    # 참여 서버 목록 출력
    for guild in bot.guilds:
        print(f'   📍 {guild.name} (ID: {guild.id}, 멤버: {guild.member_count}명)')
    
    # 관리자 설정 확인
    if ADMIN_CHANNEL_ID:
        admin_channel = bot.get_channel(int(ADMIN_CHANNEL_ID))
        if admin_channel:
            print(f'🎛️ 관리자 채널: {admin_channel.name} (서버: {admin_channel.guild.name})')
        else:
            print(f'⚠️ 관리자 채널을 찾을 수 없습니다: {ADMIN_CHANNEL_ID}')
    else:
        print('⚠️ ADMIN_CHANNEL_ID 환경변수가 설정되지 않았습니다.')
    
    # 상담용 음성 채널 설정 확인
    if CONSULTATION_VOICE_CHANNEL_ID:
        consultation_channel = bot.get_channel(int(CONSULTATION_VOICE_CHANNEL_ID))
        if consultation_channel:
            print(f'🎤 상담용 음성 채널: {consultation_channel.name} (서버: {consultation_channel.guild.name})')
        else:
            print(f'⚠️ 상담용 음성 채널을 찾을 수 없습니다: {CONSULTATION_VOICE_CHANNEL_ID}')
    else:
        print('⚠️ CONSULTATION_VOICE_CHANNEL_ID 환경변수가 설정되지 않았습니다.')
    
    # 인텐트 확인
    print(f'🔧 활성화된 인텐트:')
    print(f'   • members: {bot.intents.members}')
    print(f'   • guilds: {bot.intents.guilds}')
    print(f'   • voice_states: {bot.intents.voice_states}')
    print(f'   • message_content: {bot.intents.message_content}')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ {len(synced)}개의 슬래시 커맨드가 동기화되었습니다!')
    except Exception as e:
        print(f'❌ 커맨드 동기화 실패: {e}')

# ========== 슬래시 커맨드들 ==========

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
    
    # 첫 번째 항목(현재 상담 중)을 완료하는 경우 상담 상태 리셋
    if ticket_index == 0:
        consultation_in_progress = False
    
    completed_ticket = waiting_queue.pop(ticket_index)
    
    # 상담 완료된 사용자를 음성 채널에서 연결 끊기
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
    consultation_in_progress = False  # 상담 상태도 리셋
    
    embed = discord.Embed(
        title="🔄 대기열 초기화",
        description=f"{previous_count}개의 대기 중인 상담이 초기화되었습니다.",
        color=0xff0000
    )
    embed.timestamp = datetime.now()
    
    await interaction.response.send_message(embed=embed)
    await update_admin_panel()

# ========== 관리자 전용 명령어들 ==========

@bot.tree.command(name="관리자패널", description="관리자 패널을 생성합니다 (관리자 전용)")
async def admin_panel_command(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    await interaction.response.send_message("🎛️ 관리자 패널을 생성했습니다.", ephemeral=True)
    await update_admin_panel()

@bot.tree.command(name="이동", description="특정 사용자를 상담용 음성 채널로 이동시킵니다 (관리자 전용)")
@app_commands.describe(
    사용자="이동시킬 사용자",
    번호="번호표 번호 (선택사항)"
)
async def move_user_command(interaction: discord.Interaction, 사용자: discord.Member = None, 번호: int = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    user_id = None
    
    if 번호:
        # 번호표 번호로 사용자 찾기
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
    
    await interaction.response.send_message("🔊 사용자를 음성 채널로 이동 중...", ephemeral=True)
    success = await move_user_to_consultation_channel(user_id, interaction)
    
    if success and 번호:
        ticket = next((ticket for ticket in waiting_queue if ticket['number'] == 번호), None)
        if ticket:
            embed = discord.Embed(
                title="🔊 사용자 이동 완료",
                description=f"**{ticket['number']}번** {ticket['username']}님을 상담용 음성 채널로 이동했습니다.",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)

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
    
    for i, ticket in enumerate(waiting_queue[:5]):  # 최대 5개만 표시
        user_id = ticket['user_id']
        username = ticket['username']
        
        # 사용자 검색 시도
        member = None
        found_guild = None
        
        # 현재 길드에서 검색
        member = interaction.guild.get_member(user_id)
        if member:
            found_guild = interaction.guild.name
        else:
            # 다른 길드에서 검색
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
        # 번호표 번호로 사용자 찾기
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

@bot.tree.command(name="공지", description="특정 채널에 공지사항을 전송합니다 (관리자 전용)")
@app_commands.describe(
    채널="메시지를 보낼 채널",
    메시지="전송할 메시지 내용"
)
async def announcement_command(interaction: discord.Interaction, 채널: discord.TextChannel, 메시지: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return
    
    try:
        embed = discord.Embed(
            title="📢 공지사항",
            description=메시지,
            color=0xff6b35
        )
        embed.set_footer(text=f"관리자: {interaction.user.display_name}")
        embed.timestamp = datetime.now()
        
        await 채널.send(embed=embed)
        await interaction.response.send_message(f"✅ {채널.mention}에 공지사항을 전송했습니다.", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {채널.mention}에 메시지를 보낼 권한이 없습니다.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 메시지 전송 실패: {e}", ephemeral=True)

# 에러 핸들링
@bot.event
async def on_command_error(ctx, error):
    print(f'❌ 에러 발생: {error}')

# 봇 실행
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))