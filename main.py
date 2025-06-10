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
bot = commands.Bot(command_prefix='!', intents=intents)

# 번호표 시스템 데이터
ticket_number = 1
waiting_queue = []
consultation_in_progress = False  # 현재 상담 진행 중 여부

# 관리자 설정 (환경변수에서 가져오기)
ADMIN_CHANNEL_ID = os.getenv('ADMIN_CHANNEL_ID')

# 상담 종류 옵션
counseling_types = [
    {"label": "진로 상담", "value": "career", "emoji": "🎯"},
    {"label": "공부 상담", "value": "study", "emoji": "📚"},
    {"label": "프로젝트 고민", "value": "project", "emoji": "💡"},
    {"label": "기타", "value": "other", "emoji": "💬"}
]

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
        
        embed = discord.Embed(
            title="✅ 상담 완료",
            description=f"**{completed_ticket['number']}번** 상담이 완료되었습니다.",
            color=0xff0000
        )
        embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
        embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
        embed.add_field(name="남은 대기", value=f"{len(waiting_queue)}명", inline=True)
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
            
            embed = discord.Embed(
                title="✅ 특정 번호 완료",
                description=f"**{completed_ticket['number']}번** 상담이 완료되었습니다.",
                color=0xff0000
            )
            embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
            embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
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
    
    # 관리자 설정 확인
    if ADMIN_CHANNEL_ID:
        admin_channel = bot.get_channel(int(ADMIN_CHANNEL_ID))
        if admin_channel:
            print(f'🎛️ 관리자 채널: {admin_channel.name}')
        else:
            print(f'⚠️ 관리자 채널을 찾을 수 없습니다: {ADMIN_CHANNEL_ID}')
    else:
        print('⚠️ ADMIN_CHANNEL_ID 환경변수가 설정되지 않았습니다.')
    
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
        value="• 번호표 발급 후 상담 종류를 선택해주세요\n• 순서대로 상담이 진행됩니다\n• 대기 시간은 상황에 따라 달라질 수 있습니다",
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
    
    embed = discord.Embed(
        title="✅ 상담 완료",
        color=0x00ff00
    )
    embed.add_field(name="번호표", value=f"{completed_ticket['number']}번", inline=True)
    embed.add_field(name="상담 종류", value=get_counseling_type_label(completed_ticket['type']), inline=True)
    embed.add_field(name="상담자", value=completed_ticket['username'], inline=True)
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