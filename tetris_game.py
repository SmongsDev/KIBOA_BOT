import discord
import asyncio
import random
from datetime import datetime
from typing import List, Tuple, Optional
from enum import Enum

# 테트리스 조각 정의
TETROMINOES = {
    'I': [
        ['.....',
         '..#..',
         '..#..',
         '..#..',
         '..#..'],
        ['.....',
         '.....',
         '####.',
         '.....',
         '.....']
    ],
    'O': [
        ['.....',
         '.....',
         '.##..',
         '.##..',
         '.....']
    ],
    'T': [
        ['.....',
         '.....',
         '.#...',
         '###..',
         '.....'],
        ['.....',
         '.....',
         '.#...',
         '.##..',
         '.#...'],
        ['.....',
         '.....',
         '.....',
         '###..',
         '.#...'],
        ['.....',
         '.....',
         '.#...',
         '##...',
         '.#...']
    ],
    'S': [
        ['.....',
         '.....',
         '.##..',
         '##...',
         '.....'],
        ['.....',
         '.#...',
         '.##..',
         '..#..',
         '.....']
    ],
    'Z': [
        ['.....',
         '.....',
         '##...',
         '.##..',
         '.....'],
        ['.....',
         '..#..',
         '.##..',
         '.#...',
         '.....']
    ],
    'J': [
        ['.....',
         '.#...',
         '.#...',
         '##...',
         '.....'],
        ['.....',
         '.....',
         '#....',
         '###..',
         '.....'],
        ['.....',
         '.##..',
         '.#...',
         '.#...',
         '.....'],
        ['.....',
         '.....',
         '###..',
         '..#..',
         '.....']
    ],
    'L': [
        ['.....',
         '..#..',
         '..#..',
         '.##..',
         '.....'],
        ['.....',
         '.....',
         '###..',
         '#....',
         '.....'],
        ['.....',
         '##...',
         '.#...',
         '.#...',
         '.....'],
        ['.....',
         '.....',
         '..#..',
         '###..',
         '.....']
    ]
}

class TetrisGame:
    """테트리스 게임 로직"""
    
    def __init__(self, width=10, height=20):
        self.width = width
        self.height = height
        self.board = [[0 for _ in range(width)] for _ in range(height)]
        
        # 게임 상태
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.fall_time = 0
        self.fall_speed = 500  # 밀리초
        self.start_time = datetime.now()  # 게임 시작 시간
        
        # 현재 조각
        self.current_piece = self.get_new_piece()
        self.next_piece = self.get_new_piece()
        
        # 게임 상태
        self.game_over = False
        self.paused = False
    
    def get_new_piece(self):
        """새로운 테트리스 조각 생성"""
        shape = random.choice(list(TETROMINOES.keys()))
        return {
            'shape': shape,
            'rotation': 0,
            'x': self.width // 2 - 2,
            'y': 0
        }
    
    def get_piece_blocks(self, piece):
        """조각의 블록 위치 반환"""
        shape = piece['shape']
        rotation = piece['rotation']
        template = TETROMINOES[shape][rotation % len(TETROMINOES[shape])]
        
        blocks = []
        for y, row in enumerate(template):
            for x, cell in enumerate(row):
                if cell == '#':
                    blocks.append((piece['x'] + x, piece['y'] + y))
        return blocks
    
    def is_valid_position(self, piece, dx=0, dy=0, rotation=None):
        """조각이 유효한 위치에 있는지 확인"""
        if rotation is None:
            rotation = piece['rotation']
        
        test_piece = {
            'shape': piece['shape'],
            'rotation': rotation,
            'x': piece['x'] + dx,
            'y': piece['y'] + dy
        }
        
        blocks = self.get_piece_blocks(test_piece)
        
        for x, y in blocks:
            if x < 0 or x >= self.width or y >= self.height:
                return False
            if y >= 0 and self.board[y][x] != 0:
                return False
        
        return True
    
    def place_piece(self, piece):
        """조각을 보드에 고정"""
        blocks = self.get_piece_blocks(piece)
        shape_num = list(TETROMINOES.keys()).index(piece['shape']) + 1
        
        for x, y in blocks:
            if y >= 0:
                self.board[y][x] = shape_num
        
        # 라인 제거 체크
        self.clear_lines()
        
        # 새 조각 생성
        self.current_piece = self.next_piece
        self.next_piece = self.get_new_piece()
        
        # 게임 오버 체크
        if not self.is_valid_position(self.current_piece):
            self.game_over = True
    
    def clear_lines(self):
        """완성된 라인 제거"""
        lines_to_clear = []
        
        for y in range(self.height):
            if all(self.board[y][x] != 0 for x in range(self.width)):
                lines_to_clear.append(y)
        
        # 라인 제거
        for y in sorted(lines_to_clear, reverse=True):
            del self.board[y]
            self.board.insert(0, [0 for _ in range(self.width)])
        
        # 점수 계산
        if lines_to_clear:
            self.lines_cleared += len(lines_to_clear)
            
            # 점수 계산 (테트리스 표준)
            line_scores = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += line_scores.get(len(lines_to_clear), 800) * self.level
            
            # 레벨 업 (10라인마다)
            new_level = (self.lines_cleared // 10) + 1
            if new_level > self.level:
                self.level = new_level
                self.fall_speed = max(50, 500 - (self.level - 1) * 50)
    
    def move_piece(self, dx, dy):
        """조각 이동"""
        if self.game_over or self.paused:
            return False
        
        if self.is_valid_position(self.current_piece, dx, dy):
            self.current_piece['x'] += dx
            self.current_piece['y'] += dy
            return True
        elif dy > 0:  # 아래로 이동할 수 없으면 고정
            self.place_piece(self.current_piece)
            return True
        
        return False
    
    def rotate_piece(self):
        """조각 회전"""
        if self.game_over or self.paused:
            return False
        
        new_rotation = (self.current_piece['rotation'] + 1) % len(TETROMINOES[self.current_piece['shape']])
        
        if self.is_valid_position(self.current_piece, rotation=new_rotation):
            self.current_piece['rotation'] = new_rotation
            return True
        
        return False
    
    def hard_drop(self):
        """하드 드롭 (바닥까지 떨어뜨리기)"""
        if self.game_over or self.paused:
            return False
        
        while self.is_valid_position(self.current_piece, 0, 1):
            self.current_piece['y'] += 1
            self.score += 2  # 하드 드롭 보너스
        
        self.place_piece(self.current_piece)
        return True
    
    def get_play_time(self):
        """플레이 시간 계산 (초 단위)"""
        if hasattr(self, 'start_time'):
            return int((datetime.now() - self.start_time).total_seconds())
        return 0
    
    def get_board_display(self):
        """보드 표시용 문자열 생성"""
        # 보드 복사
        display_board = [row[:] for row in self.board]
        
        # 현재 조각 표시
        if not self.game_over:
            blocks = self.get_piece_blocks(self.current_piece)
            shape_num = list(TETROMINOES.keys()).index(self.current_piece['shape']) + 1
            
            for x, y in blocks:
                if 0 <= x < self.width and 0 <= y < self.height:
                    display_board[y][x] = shape_num
        
        # 이모지로 변환
        emoji_map = {
            0: '⬛',  # 빈 공간
            1: '🟦',  # I 조각 (파랑)
            2: '🟨',  # O 조각 (노랑)
            3: '🟪',  # T 조각 (보라)
            4: '🟩',  # S 조각 (초록)
            5: '🟥',  # Z 조각 (빨강)
            6: '🟫',  # J 조각 (갈색)
            7: '🟧'   # L 조각 (주황)
        }
        
        lines = []
        for row in display_board:
            line = ''.join(emoji_map.get(cell, '⬜') for cell in row)
            lines.append(line)
        
        return '\n'.join(lines)

class TetrisView(discord.ui.View):
    """테트리스 게임 UI"""
    
    def __init__(self, user_id: int, record_callback=None):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.game = TetrisGame()
        self.user_id = user_id
        self.message = None
        self.auto_fall_task = None
        self.record_callback = record_callback  # 기록 저장 콜백 함수
        
        # 자동 낙하 시작
        self.start_auto_fall()
    
    def start_auto_fall(self):
        """자동 낙하 시작"""
        if self.auto_fall_task is None or self.auto_fall_task.done():
            self.auto_fall_task = asyncio.create_task(self.auto_fall_loop())
    
    async def auto_fall_loop(self):
        """자동 낙하 루프"""
        while not self.game.game_over and not self.game.paused:
            try:
                await asyncio.sleep(self.game.fall_speed / 1000.0)
                
                if not self.game.paused and not self.game.game_over:
                    moved = self.game.move_piece(0, 1)  # 아래로 이동
                    
                    if moved and self.message and not self.game.game_over:
                        try:
                            embed = self.create_embed()
                            await self.message.edit(embed=embed, view=self)
                        except (discord.NotFound, discord.HTTPException):
                            break
                    elif self.game.game_over:
                        await self.handle_game_over()
                        break
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ 자동 낙하 오류: {e}")
                break
    
    async def handle_game_over(self):
        """게임 오버 처리"""
        if self.auto_fall_task:
            self.auto_fall_task.cancel()
        
        # 게임 기록 저장
        try:
            # 사용자 정보 가져오기
            username = "Unknown"
            try:
                if self.message and self.message.guild:
                    member = self.message.guild.get_member(self.user_id)
                    if member:
                        username = member.display_name
            except:
                pass
            
            # 플레이 시간 계산
            play_time = self.game.get_play_time()
            
            if self.record_callback:
                success = self.record_callback(
                    user_id=self.user_id,
                    username=username,
                    score=self.game.score,
                    level=self.game.level,
                    lines_cleared=self.game.lines_cleared,
                    play_time=play_time
                )
                if success:
                    print(f"✅ 테트리스 기록 저장 완료: {username} - {self.game.score:,}점")
                else:
                    print(f"❌ 테트리스 기록 저장 실패: {username}")
            else:
                print("⚠️ 기록 저장 콜백이 설정되지 않았습니다.")
                
        except Exception as e:
            print(f"⚠️ 게임 기록 저장 중 오류: {e}")
        
        self.clear_items()
        
        if self.message:
            embed = discord.Embed(
                title="💀 게임 오버!",
                color=0xff0000
            )
            embed.add_field(name="최종 점수", value=f"{self.game.score:,}점", inline=True)
            embed.add_field(name="도달 레벨", value=f"{self.game.level}레벨", inline=True)
            embed.add_field(name="클리어한 라인", value=f"{self.game.lines_cleared}개", inline=True)
            embed.add_field(name="플레이 시간", value=f"{self.game.get_play_time()}초", inline=True)
            embed.add_field(name="🎯 성과", value=self.get_achievement_text(), inline=False)
            embed.set_footer(text="게임 기록이 저장되었습니다! /게임통계로 순위를 확인해보세요.")
            embed.timestamp = datetime.now()
            
            try:
                await self.message.edit(embed=embed, view=self)
            except (discord.NotFound, discord.HTTPException):
                pass
        
        self.stop()
    
    def get_achievement_text(self):
        """성과 텍스트 생성"""
        achievements = []
        
        if self.game.score >= 100000:
            achievements.append("🏆 10만점 돌파!")
        elif self.game.score >= 50000:
            achievements.append("⭐ 5만점 달성!")
        elif self.game.score >= 10000:
            achievements.append("✨ 1만점 돌파!")
        
        if self.game.level >= 10:
            achievements.append("🚀 레벨 10 도달!")
        elif self.game.level >= 5:
            achievements.append("🔥 레벨 5 달성!")
        
        if self.game.lines_cleared >= 100:
            achievements.append("📏 100라인 클리어!")
        elif self.game.lines_cleared >= 50:
            achievements.append("📐 50라인 클리어!")
        
        return " ".join(achievements) if achievements else "첫 게임을 완주하셨네요! 🎮"
    
    def create_embed(self):
        """게임 상태 임베드 생성"""
        if self.game.game_over:
            embed = discord.Embed(
                title="💀 게임 오버!",
                color=0xff0000
            )
        elif self.game.paused:
            embed = discord.Embed(
                title="⏸️ 테트리스 (일시정지)",
                color=0xffaa00
            )
        else:
            embed = discord.Embed(
                title="🎮 테트리스",
                color=0x00aaff
            )
        
        # 게임 보드
        board_display = self.game.get_board_display()
        embed.add_field(
            name="🎯 게임 보드",
            value=f"```\n{board_display}\n```",
            inline=False
        )
        
        # 게임 정보
        embed.add_field(name="점수", value=f"{self.game.score:,}", inline=True)
        embed.add_field(name="레벨", value=f"{self.game.level}", inline=True)
        embed.add_field(name="라인", value=f"{self.game.lines_cleared}", inline=True)
        
        # 다음 조각 정보
        next_shape = self.game.next_piece['shape']
        next_emoji = {
            'I': '🟦', 'O': '🟨', 'T': '🟪', 'S': '🟩',
            'Z': '🟥', 'J': '🟫', 'L': '🟧'
        }.get(next_shape, '⬜')
        
        embed.add_field(
            name="다음 조각",
            value=f"{next_emoji} {next_shape}",
            inline=True
        )
        
        # 플레이 시간
        embed.add_field(
            name="플레이 시간",
            value=f"{self.game.get_play_time()}초",
            inline=True
        )
        
        if self.game.paused:
            embed.add_field(
                name="⏸️ 일시정지",
                value="계속하려면 ⏸️ 버튼을 누르세요",
                inline=False
            )
        
        embed.set_footer(text="아래 버튼들로 조작하세요!")
        embed.timestamp = datetime.now()
        
        return embed
    
    async def update_display(self):
        """화면 업데이트"""
        if self.message and not self.game.game_over:
            embed = self.create_embed()
            try:
                await self.message.edit(embed=embed, view=self)
            except (discord.NotFound, discord.HTTPException):
                pass
    
    # 컨트롤 버튼들
    @discord.ui.button(label='⬅️', style=discord.ButtonStyle.secondary, row=0)
    async def move_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        self.game.move_piece(-1, 0)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='🔄', style=discord.ButtonStyle.secondary, row=0)
    async def rotate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        self.game.rotate_piece()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='➡️', style=discord.ButtonStyle.secondary, row=0)
    async def move_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        self.game.move_piece(1, 0)
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='⬇️', style=discord.ButtonStyle.secondary, row=1)
    async def soft_drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        moved = self.game.move_piece(0, 1)
        if moved:
            self.game.score += 1  # 소프트 드롭 보너스
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        if self.game.game_over:
            await self.handle_game_over()
    
    @discord.ui.button(label='⏬', style=discord.ButtonStyle.primary, row=1)
    async def hard_drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        self.game.hard_drop()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        if self.game.game_over:
            await self.handle_game_over()
    
    @discord.ui.button(label='⏸️', style=discord.ButtonStyle.secondary, row=1)
    async def pause_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
        
        self.game.paused = not self.game.paused
        
        if not self.game.paused:
            self.start_auto_fall()  # 일시정지 해제 시 자동 낙하 재시작
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='❌', style=discord.ButtonStyle.danger, row=2)
    async def quit_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 다른 사람의 게임입니다!", ephemeral=True)
            return
            
        if self.auto_fall_task:
            self.auto_fall_task.cancel()
        
        # 게임 기록 저장
        try:
            username = interaction.user.display_name
            play_time = self.game.get_play_time()
            
            if self.record_callback:
                success = self.record_callback(
                    user_id=interaction.user.id,
                    username=username,
                    score=self.game.score,
                    level=self.game.level,
                    lines_cleared=self.game.lines_cleared,
                    play_time=play_time
                )
                if success:
                    print(f"✅ 테트리스 기록 저장 완료: {username} - {self.game.score:,}점")
            else:
                print("⚠️ 기록 저장 콜백이 설정되지 않았습니다.")
                
        except Exception as e:
            print(f"⚠️ 게임 기록 저장 중 오류: {e}")
        
        embed = discord.Embed(
            title="🎮 테트리스 게임 종료",
            description=f"최종 점수: **{self.game.score:,}점**\n레벨: **{self.game.level}**\n클리어한 라인: **{self.game.lines_cleared}개**\n플레이 시간: **{self.game.get_play_time()}초**",
            color=0xff9900
        )
        embed.set_footer(text="게임 기록이 저장되었습니다! /게임통계로 순위를 확인해보세요.")
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def on_timeout(self):
        """타임아웃 시 게임 종료"""
        if self.auto_fall_task:
            self.auto_fall_task.cancel()
        
        # 게임 기록 저장 (타임아웃)
        try:
            if self.record_callback:
                success = self.record_callback(
                    user_id=self.user_id,
                    username="Unknown",  # 타임아웃시 사용자명 불명
                    score=self.game.score,
                    level=self.game.level,
                    lines_cleared=self.game.lines_cleared,
                    play_time=self.game.get_play_time()
                )
                if success:
                    print(f"✅ 테트리스 기록 저장 완료 (타임아웃): {self.game.score:,}점")
        except Exception as e:
            print(f"⚠️ 타임아웃 게임 기록 저장 중 오류: {e}")
        
        if self.message:
            try:
                embed = discord.Embed(
                    title="⏰ 테트리스 - 시간 초과",
                    description="게임이 비활성 상태로 종료되었습니다.",
                    color=0x808080
                )
                embed.add_field(
                    name="최종 점수",
                    value=f"{self.game.score:,}점",
                    inline=True
                )
                await self.message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass
        
        self.stop()

# 게임 시작 함수
async def start_tetris_game(interaction: discord.Interaction, record_callback=None):
    """테트리스 게임 시작"""
    user_id = interaction.user.id
    
    # 새 게임 시작
    view = TetrisView(user_id, record_callback=record_callback)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    view.message = message
    
    print(f"🎮 테트리스 게임 시작: {interaction.user.display_name}")

# 게임 현황 확인 함수 (단순화됨)
def get_game_status():
    """현재 테트리스 게임 진행 상황 (단순 메시지)"""
    return "🎯 테트리스 게임은 /테트리스 명령어로 시작할 수 있습니다!"