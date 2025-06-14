"""
가위바위보 게임 모듈
삼세판 1대1 가위바위보 게임
"""

import discord
import asyncio
import random
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List

class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing" 
    FINISHED = "finished"

class Choice(Enum):
    ROCK = "바위"
    PAPER = "보"
    SCISSORS = "가위"

class RockPaperScissorsGame:
    """가위바위보 게임 로직"""
    
    CHOICE_EMOJIS = {
        Choice.ROCK: "🪨",
        Choice.PAPER: "📄", 
        Choice.SCISSORS: "✂️"
    }
    
    def __init__(self, host_id: int):
        self.host_id = host_id
        self.opponent_id: Optional[int] = None
        self.state = GameState.WAITING
        
        # 삼세판 관리
        self.rounds_played = 0
        self.max_rounds = 3
        self.host_wins = 0
        self.opponent_wins = 0
        
        # 현재 라운드
        self.current_round = 1
        self.host_choice: Optional[Choice] = None
        self.opponent_choice: Optional[Choice] = None
        
        # 게임 히스토리
        self.round_history: List[Dict] = []
        
        # 라운드 결과 계산 여부 (중복 점수 방지)
        self.round_result_calculated = False
        
        # 게임 시작 시간
        self.start_time = datetime.now()
    
    def join_game(self, user_id: int) -> bool:
        """게임에 참가"""
        if self.state != GameState.WAITING or user_id == self.host_id:
            return False
        
        self.opponent_id = user_id
        self.state = GameState.PLAYING
        return True
    
    def make_choice(self, user_id: int, choice: Choice) -> bool:
        """선택하기"""
        if self.state != GameState.PLAYING:
            return False
        
        if user_id == self.host_id:
            if self.host_choice is not None:  # 이미 선택한 경우
                return False
            self.host_choice = choice
        elif user_id == self.opponent_id:
            if self.opponent_choice is not None:  # 이미 선택한 경우
                return False
            self.opponent_choice = choice
        else:
            return False
        
        return True
    
    def both_choices_made(self) -> bool:
        """양쪽 모두 선택했는지 확인"""
        return self.host_choice is not None and self.opponent_choice is not None
    
    def get_round_result(self) -> Dict:
        """현재 라운드 결과 계산"""
        if not self.both_choices_made():
            return {}
        
        # 이미 결과가 계산된 경우 기존 결과 반환 (중복 점수 증가 방지)
        if self.round_result_calculated:
            # 히스토리에서 현재 라운드 결과 찾기
            for round_data in self.round_history:
                if round_data["round"] == self.current_round:
                    return round_data
            return {}
        
        host_choice = self.host_choice
        opponent_choice = self.opponent_choice
        
        # 승부 판정
        winner = None
        if host_choice == opponent_choice:
            result = "무승부"
        elif (
            (host_choice == Choice.ROCK and opponent_choice == Choice.SCISSORS) or
            (host_choice == Choice.PAPER and opponent_choice == Choice.ROCK) or
            (host_choice == Choice.SCISSORS and opponent_choice == Choice.PAPER)
        ):
            result = "호스트 승리"
            winner = self.host_id
            self.host_wins += 1
        else:
            result = "상대방 승리"
            winner = self.opponent_id
            self.opponent_wins += 1
        
        round_data = {
            "round": self.current_round,
            "host_choice": host_choice,
            "opponent_choice": opponent_choice,
            "result": result,
            "winner": winner
        }
        
        self.round_history.append(round_data)
        self.round_result_calculated = True  # 결과 계산 완료 표시
        
        return round_data
    
    def next_round(self):
        """다음 라운드로"""
        self.current_round += 1
        self.rounds_played += 1
        self.host_choice = None
        self.opponent_choice = None
        self.round_result_calculated = False  # 새 라운드에서 결과 계산 플래그 리셋
        
        # 게임 종료 체크 (2승 먼저 하거나 3라운드 완료)
        if self.host_wins >= 2 or self.opponent_wins >= 2 or self.rounds_played >= 3:
            self.state = GameState.FINISHED
    
    def get_game_winner(self) -> Optional[int]:
        """최종 승자 반환"""
        if self.state != GameState.FINISHED:
            return None
        
        if self.host_wins > self.opponent_wins:
            return self.host_id
        elif self.opponent_wins > self.host_wins:
            return self.opponent_id
        else:
            return None  # 무승부
    
    def get_score_text(self) -> str:
        """현재 스코어 텍스트"""
        return f"{self.host_wins} : {self.opponent_wins}"
    
    def get_play_time(self):
        """플레이 시간 계산 (초 단위)"""
        if hasattr(self, 'start_time'):
            return int((datetime.now() - self.start_time).total_seconds())
        return 0

class RockPaperScissorsView(discord.ui.View):
    """가위바위보 게임 UI"""
    
    def __init__(self, host_id: int, record_callback=None):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.game = RockPaperScissorsGame(host_id)
        self.host_id = host_id
        self.message = None
        self.record_callback = record_callback  # 기록 저장 콜백 함수
        
        # 초기에는 참가 버튼만 표시
        self.setup_waiting_buttons()
    
    def setup_waiting_buttons(self):
        """대기 중 버튼 설정"""
        self.clear_items()
        self.add_item(JoinGameButton())
    
    def setup_playing_buttons(self):
        """게임 중 버튼 설정"""
        self.clear_items()
        
        # 가위바위보 선택 버튼들
        self.add_item(ChoiceButton(Choice.ROCK, "🪨 바위", discord.ButtonStyle.secondary))
        self.add_item(ChoiceButton(Choice.PAPER, "📄 보", discord.ButtonStyle.secondary))
        self.add_item(ChoiceButton(Choice.SCISSORS, "✂️ 가위", discord.ButtonStyle.secondary))
        
        # 게임 포기 버튼
        self.add_item(QuitGameButton())
    
    def create_embed(self) -> discord.Embed:
        """게임 상태에 따른 임베드 생성"""
        if self.game.state == GameState.WAITING:
            return self.create_waiting_embed()
        elif self.game.state == GameState.PLAYING:
            return self.create_playing_embed()
        else:  # FINISHED
            return self.create_finished_embed()
    
    def create_waiting_embed(self) -> discord.Embed:
        """대기 중 임베드"""
        embed = discord.Embed(
            title="🎮 가위바위보 게임",
            description="삼세판 가위바위보 게임에 참가하세요!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="🎯 게임 규칙",
            value="• 삼세판 (3라운드 중 2승)\n• 먼저 2승하면 승리!\n• 5분 제한시간",
            inline=False
        )
        
        embed.add_field(
            name="👥 참가자",
            value=f"**호스트:** <@{self.host_id}>\n**상대방:** 참가 대기 중...",
            inline=False
        )
        
        embed.set_footer(text="'참가하기' 버튼을 눌러서 게임에 참가하세요!")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_playing_embed(self) -> discord.Embed:
        """게임 중 임베드"""
        embed = discord.Embed(
            title=f"🎮 가위바위보 - {self.game.current_round}라운드",
            color=0xffa500
        )
        
        # 현재 스코어
        embed.add_field(
            name="📊 현재 스코어",
            value=f"<@{self.host_id}> **{self.game.host_wins}** : **{self.game.opponent_wins}** <@{self.game.opponent_id}>",
            inline=False
        )
        
        # 선택 상태
        host_status = "✅ 선택 완료" if self.game.host_choice else "⏳ 선택 대기"
        opponent_status = "✅ 선택 완료" if self.game.opponent_choice else "⏳ 선택 대기"
        
        embed.add_field(
            name="🎯 선택 상태",
            value=f"**호스트:** {host_status}\n**상대방:** {opponent_status}",
            inline=True
        )
        
        # 플레이 시간
        embed.add_field(
            name="⏱️ 플레이 시간",
            value=f"{self.game.get_play_time()}초",
            inline=True
        )
        
        # 라운드 히스토리
        if self.game.round_history:
            history_text = ""
            for round_data in self.game.round_history[-3:]:  # 최근 3라운드만
                host_emoji = self.game.CHOICE_EMOJIS[round_data["host_choice"]]
                opponent_emoji = self.game.CHOICE_EMOJIS[round_data["opponent_choice"]]
                result = round_data["result"]
                history_text += f"**{round_data['round']}R:** {host_emoji} vs {opponent_emoji} - {result}\n"
            
            embed.add_field(
                name="📋 라운드 결과",
                value=history_text,
                inline=False
            )
        
        # 양쪽 모두 선택했으면 결과 표시
        if self.game.both_choices_made():
            round_result = self.game.get_round_result()
            if round_result:  # 결과가 있을 때만 표시
                host_emoji = self.game.CHOICE_EMOJIS[round_result["host_choice"]]
                opponent_emoji = self.game.CHOICE_EMOJIS[round_result["opponent_choice"]]
                
                embed.add_field(
                    name=f"🎯 {self.game.current_round}라운드 결과",
                    value=f"{host_emoji} vs {opponent_emoji}\n**{round_result['result']}**",
                    inline=False
                )
        
        embed.set_footer(text="가위, 바위, 보 중 하나를 선택하세요!")
        embed.timestamp = datetime.now()
        
        return embed
    
    def create_finished_embed(self) -> discord.Embed:
        """게임 완료 임베드"""
        winner_id = self.game.get_game_winner()
        
        if winner_id:
            embed = discord.Embed(
                title="🏆 가위바위보 게임 완료!",
                description=f"🎉 승자: <@{winner_id}>",
                color=0xffd700
            )
        else:
            embed = discord.Embed(
                title="🤝 가위바위보 게임 완료!",
                description="무승부입니다!",
                color=0x808080
            )
        
        # 최종 스코어
        embed.add_field(
            name="📊 최종 스코어",
            value=f"<@{self.host_id}> **{self.game.host_wins}** : **{self.game.opponent_wins}** <@{self.game.opponent_id}>",
            inline=False
        )
        
        # 플레이 시간
        embed.add_field(
            name="⏱️ 총 플레이 시간",
            value=f"{self.game.get_play_time()}초",
            inline=True
        )
        
        # 전체 라운드 결과
        if self.game.round_history:
            history_text = ""
            for round_data in self.game.round_history:
                host_emoji = self.game.CHOICE_EMOJIS[round_data["host_choice"]]
                opponent_emoji = self.game.CHOICE_EMOJIS[round_data["opponent_choice"]]
                result = round_data["result"]
                history_text += f"**{round_data['round']}R:** {host_emoji} vs {opponent_emoji} - {result}\n"
            
            embed.add_field(
                name="📋 전체 결과",
                value=history_text,
                inline=False
            )
        
        embed.set_footer(text="게임이 종료되었습니다. 기록이 저장되었습니다! /게임통계로 순위를 확인해보세요.")
        embed.timestamp = datetime.now()
        
        return embed
    
    async def update_display(self):
        """화면 업데이트"""
        if self.message:
            embed = self.create_embed()
            try:
                await self.message.edit(embed=embed, view=self)
            except (discord.NotFound, discord.HTTPException):
                pass
    
    async def save_game_record(self, reason="completed"):
        """게임 기록 저장"""
        try:
            # 사용자 정보 가져오기
            host_name = "Unknown"
            opponent_name = "Unknown"
            
            try:
                if hasattr(self, 'message') and self.message and self.message.guild:
                    host_member = self.message.guild.get_member(self.host_id)
                    opponent_member = self.message.guild.get_member(self.game.opponent_id) if self.game.opponent_id else None
                    if host_member:
                        host_name = host_member.display_name
                    if opponent_member:
                        opponent_name = opponent_member.display_name
            except:
                pass
            
            # 기록 저장 콜백 함수 호출
            if self.record_callback and self.game.opponent_id:
                success = self.record_callback(
                    host_id=self.host_id,
                    host_name=host_name,
                    opponent_id=self.game.opponent_id,
                    opponent_name=opponent_name,
                    winner_id=self.game.get_game_winner(),
                    host_wins=self.game.host_wins,
                    opponent_wins=self.game.opponent_wins,
                    rounds_played=self.game.rounds_played
                )
                if success:
                    winner_name = host_name if self.game.get_game_winner() == self.host_id else opponent_name if self.game.get_game_winner() == self.game.opponent_id else "무승부"
                    print(f"✅ 가위바위보 기록 저장 완료: {host_name} vs {opponent_name}, 승자: {winner_name} ({reason})")
                else:
                    print(f"❌ 가위바위보 기록 저장 실패: {host_name} vs {opponent_name} ({reason})")
            else:
                print(f"⚠️ 가위바위보 기록 저장 건너뜀: 콜백 없음 또는 상대방 없음 ({reason})")
                
        except Exception as e:
            print(f"⚠️ 가위바위보 기록 저장 중 오류 ({reason}): {e}")
    
    async def on_timeout(self):
        """타임아웃 처리"""
        # 게임이 진행 중이었다면 기록 저장
        if self.game.state == GameState.PLAYING and self.game.opponent_id:
            await self.save_game_record("timeout")
        
        if self.message:
            try:
                embed = discord.Embed(
                    title="⏰ 가위바위보 게임 시간 초과",
                    description="게임이 비활성 상태로 종료되었습니다.",
                    color=0x808080
                )
                if self.game.opponent_id:
                    embed.add_field(
                        name="📊 최종 스코어",
                        value=f"<@{self.host_id}> {self.game.host_wins} : {self.game.opponent_wins} <@{self.game.opponent_id}>",
                        inline=False
                    )
                    embed.add_field(
                        name="⏱️ 플레이 시간",
                        value=f"{self.game.get_play_time()}초",
                        inline=True
                    )
                embed.set_footer(text="게임 기록이 저장되었습니다!")
                await self.message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        self.stop()

class JoinGameButton(discord.ui.Button):
    """게임 참가 버튼"""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="🎯 참가하기",
            emoji="🎮"
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: RockPaperScissorsView = self.view
        
        # 호스트는 참가할 수 없음
        if interaction.user.id == view.host_id:
            await interaction.response.send_message("❌ 호스트는 자신의 게임에 참가할 수 없습니다!", ephemeral=True)
            return
        
        # 게임 참가 시도
        if view.game.join_game(interaction.user.id):
            view.setup_playing_buttons()
            embed = view.create_embed()
            await interaction.response.edit_message(embed=embed, view=view)
            
            # 게임 시작 안내
            await interaction.followup.send(
                f"🎮 게임이 시작되었습니다!\n"
                f"**참가자:** <@{view.host_id}> vs <@{interaction.user.id}>\n"
                f"**규칙:** 삼세판 (먼저 2승하면 승리!)",
                ephemeral=False
            )
        else:
            await interaction.response.send_message("❌ 게임 참가에 실패했습니다.", ephemeral=True)

class ChoiceButton(discord.ui.Button):
    """가위바위보 선택 버튼"""
    
    def __init__(self, choice: Choice, label: str, style: discord.ButtonStyle):
        super().__init__(style=style, label=label)
        self.choice = choice
    
    async def callback(self, interaction: discord.Interaction):
        view: RockPaperScissorsView = self.view
        
        # 참가자가 아니면 무시
        if interaction.user.id not in [view.host_id, view.game.opponent_id]:
            await interaction.response.send_message("❌ 게임 참가자가 아닙니다!", ephemeral=True)
            return
        
        # 선택하기 시도
        if view.game.make_choice(interaction.user.id, self.choice):            
            # 양쪽 모두 선택했으면 결과 처리
            if view.game.both_choices_made():
                await asyncio.sleep(1)  # 잠깐 대기
                
                # 라운드 결과 계산 (한 번만 호출됨)
                round_result = view.game.get_round_result()
                
                # 화면 업데이트 (결과 표시)
                await view.update_display()
                await asyncio.sleep(2)  # 결과 보여주기
                
                # 다음 라운드 또는 게임 종료
                view.game.next_round()
                
                if view.game.state == GameState.FINISHED:
                    # 게임 종료 - 게임 기록 저장
                    await view.save_game_record("completed")
                    view.clear_items()
                
                await view.update_display()
            else:
                # 상대방 선택 대기
                await view.update_display()
                
            await interaction.response.defer()  # 응답 처리
        else:
            await interaction.response.send_message("❌ 이미 선택하셨거나 선택에 실패했습니다.", ephemeral=True)

class QuitGameButton(discord.ui.Button):
    """게임 포기 버튼"""
    
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="❌ 포기",
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: RockPaperScissorsView = self.view
        
        # 참가자가 아니면 무시
        if interaction.user.id not in [view.host_id, view.game.opponent_id]:
            await interaction.response.send_message("❌ 게임 참가자가 아닙니다!", ephemeral=True)
            return
        
        # 게임 강제 종료
        view.game.state = GameState.FINISHED
        
        # 포기한 사람의 반대편이 승리 (하지만 점수는 2점으로 고정)
        if interaction.user.id == view.host_id:
            view.game.opponent_wins = 2
            view.game.host_wins = 0  # 포기한 사람은 0점
        else:
            view.game.host_wins = 2
            view.game.opponent_wins = 0  # 포기한 사람은 0점
        
        # 게임 기록 저장
        await view.save_game_record("quit")
        
        view.clear_items()
        
        embed = discord.Embed(
            title="❌ 게임 포기",
            description=f"<@{interaction.user.id}>님이 게임을 포기했습니다.",
            color=0xff0000
        )
        
        winner_id = view.game.get_game_winner()
        if winner_id:
            embed.add_field(
                name="🏆 승자",
                value=f"<@{winner_id}>",
                inline=False
            )
        
        embed.add_field(
            name="⏱️ 플레이 시간",
            value=f"{view.game.get_play_time()}초",
            inline=True
        )
        
        embed.set_footer(text="게임 기록이 저장되었습니다!")
        
        await interaction.response.edit_message(embed=embed, view=view)

# 게임 시작 함수
async def start_rps_game(interaction: discord.Interaction, record_callback=None):
    """가위바위보 게임 시작"""
    user_id = interaction.user.id
    
    # 새 게임 시작
    view = RockPaperScissorsView(user_id, record_callback=record_callback)
    
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    view.message = message
    
    print(f"✂️ 가위바위보 게임 시작: {interaction.user.display_name}")

# 게임 현황 확인 함수 (단순화됨)
def get_rps_game_status():
    """현재 가위바위보 게임 진행 상황 (단순 메시지)"""
    return "✂️ 가위바위보 게임은 /가위바위보 명령어로 시작할 수 있습니다!"