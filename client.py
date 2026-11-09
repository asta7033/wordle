import sys
import os
import pygame
import requests

# 桌面 client 在本機執行，透過這個網址呼叫雲端 FastAPI server。
# 任務五：部署到 Render 後把下面網址換成自己的 Render 服務網址
# 本機測試可設定環境變數：API_BASE_URL=http://127.0.0.1:8000
# ඩamongus
API_BASE_URL = os.environ.get(
    "API_BASE_URL", "https://wordle-nfiq.onrender.com"
).rstrip("/")

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_SUBTEXT = (180, 180, 180)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色🍌
COLOR_ABSENT = (58, 58, 60)     # 灰色
COLOR_DIVIDER = (90, 90, 90)
COLOR_HARD = (230, 90, 90)

FEEDBACK_COLOR = {
    "correct": COLOR_CORRECT,
    "present": COLOR_PRESENT,
    "absent": COLOR_ABSENT,
}

pygame.init()
# 任務三：視窗寬度 500 -> 700，右側 x=500~700 為歷史紀錄面板
WIDTH, HEIGHT = 700, 650
PANEL_X = 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
info_font = pygame.font.SysFont("Arial", 16, bold=True)
tiny_font = pygame.font.SysFont("Arial", 14, bold=True)

REQUEST_TIMEOUT = 60  # Render 免費服務休眠後，第一次請求可能需要較久才會喚醒。


def safe_detail(res, default):
    """ 安全地取出 FastAPI 錯誤訊息，避免回應不是 JSON 時崩潰 """
    try:
        detail = res.json().get("detail", default)
        return detail if isinstance(detail, str) else default
    except ValueError:
        return default


class WordleGame:
    def __init__(self):
        self.game_id = None
        self.hard_mode = False
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0}
        self.reset_board()
        self.message = "Press ENTER to submit, R to restart, H for Hard Mode"
        self.start_new_game()

    def reset_board(self):
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.history = []  # [(word, [color x5]), ...] 本局已猜過的單字
        self.row = 0
        self.col = 0
        self.game_over = False

    def show_loading(self, text):
        """ 網路請求前先畫一次畫面，避免 Render 喚醒時看起來像當機 """
        self.message = text
        self.draw(screen)
        pygame.display.flip()
        pygame.event.pump()

    def update_stats(self, data):
        stats = data.get("stats")
        if isinstance(stats, dict):
            self.stats = stats

    def fetch_stats(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=REQUEST_TIMEOUT)
            if res.status_code == 200:
                self.stats = res.json()
        except (requests.exceptions.RequestException, ValueError):
            pass

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局（帶入 hard_mode） """
        self.show_loading("Connecting to server...")
        try:
            res = requests.post(
                f"{API_BASE_URL}/api/new-game",
                json={"hard_mode": self.hard_mode},
                timeout=REQUEST_TIMEOUT,
            )
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.reset_board()
                self.update_stats(data)
                mode = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! ({mode} mode)"
            else:
                self.game_id = None
                self.message = "Server error starting new game."
        except (requests.exceptions.RequestException, ValueError, KeyError):
            self.game_id = None
            self.message = "Cannot connect to FastAPI server! Press R to retry."

    def toggle_hard_mode(self):
        """ 任務四：按 H 切換困難模式並開始新遊戲 """
        self.hard_mode = not self.hard_mode
        self.start_new_game()

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.game_id is None:
            self.message = "No active game. Press R to retry connection."
            return

        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=REQUEST_TIMEOUT)

            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                self.update_stats(data)

                # 依據後端回傳更新格子顏色
                row_colors = [FEEDBACK_COLOR.get(f, COLOR_ABSENT) for f in feedback]
                self.colors[self.row] = row_colors
                self.history.append((guess_word, row_colors))

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    attempts_left = data.get("attempts_left", 6 - self.row)
                    if data.get("game_over") or self.row >= 6:
                        # 任務一：顯示後端揭曉的正確答案
                        answer = data.get("target_word") or "?????"
                        self.message = f"Game Over! The word was {answer}. Press R to restart."
                        self.game_over = True
                    else:
                        self.message = f"Keep guessing! ({attempts_left} tries left)"
            elif res.status_code == 400:
                detail = safe_detail(res, "Invalid guess")
                # 任務二：不在字典中 -> 不前進、不清空，玩家可用 Backspace 修改
                if "not in dictionary" in detail.lower():
                    self.message = "Not in word list!"
                else:
                    self.message = detail
            elif res.status_code == 404:
                self.message = "Game session lost. Press R to restart."
                self.game_over = True
            else:
                self.message = safe_detail(res, "Error processing guess")
        except (requests.exceptions.RequestException, ValueError, KeyError):
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            return

        if event.key == pygame.K_h:
            self.toggle_hard_mode()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.submit_guess()
        elif event.unicode and event.unicode.isascii() and event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw_top_info(self, surface):
        """ 右上角：模式與戰績 """
        if self.hard_mode:
            mode_surface = info_font.render("Mode: HARD", True, COLOR_HARD)
        else:
            mode_surface = info_font.render("Mode: Normal", True, COLOR_TEXT)
        surface.blit(mode_surface, mode_surface.get_rect(topright=(WIDTH - 12, 10)))

        s = self.stats
        stats_text = f"Total: {s.get('total_games', 0)} | Wins: {s.get('wins', 0)} | Win Rate: {s.get('win_rate', 0)}%"
        stats_surface = tiny_font.render(stats_text, True, COLOR_SUBTEXT)
        surface.blit(stats_surface, stats_surface.get_rect(topright=(WIDTH - 12, 32)))

    def draw_history_panel(self, surface):
        """ 任務三：右側歷史紀錄面板 (x: 500~700) """
        pygame.draw.line(surface, COLOR_DIVIDER, (PANEL_X, 60), (PANEL_X, HEIGHT - 80), 2)

        title = info_font.render("History", True, COLOR_TEXT)
        surface.blit(title, (PANEL_X + 20, 70))

        if not self.history:
            empty = tiny_font.render("(no guesses yet)", True, COLOR_SUBTEXT)
            surface.blit(empty, (PANEL_X + 20, 100))
            return

        tile, gap = 26, 4
        for idx, (word, row_colors) in enumerate(self.history):
            y = 100 + idx * (tile + 12)
            num = tiny_font.render(f"{idx + 1}.", True, COLOR_SUBTEXT)
            surface.blit(num, num.get_rect(midleft=(PANEL_X + 15, y + tile // 2)))
            for i, ch in enumerate(word):
                x = PANEL_X + 40 + i * (tile + gap)
                rect = pygame.Rect(x, y, tile, tile)
                pygame.draw.rect(surface, row_colors[i], rect, border_radius=3)
                ch_surface = tiny_font.render(ch, True, COLOR_TEXT)
                surface.blit(ch_surface, ch_surface.get_rect(center=rect.center))

    def draw(self, surface):
        surface.fill(COLOR_BG)
        # 繪製 6x5 網格
        margin_x, margin_y = 75, 70
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)

                # 畫背景框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY and not (r < len(self.history)):
                    border = (130, 130, 130) if (r == self.row and not self.game_over) else (80, 80, 80)
                    pygame.draw.rect(surface, border, rect, width=2, border_radius=4)

                # 畫字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        self.draw_top_info(surface)
        self.draw_history_panel(surface)

        # 畫底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 50))
        surface.blit(msg_surface, msg_rect)

        hint = tiny_font.render("ENTER: submit   BACKSPACE: delete   R: restart   H: toggle Hard Mode", True, COLOR_SUBTEXT)
        surface.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 20)))


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)


if __name__ == "__main__":
    main()
    # ／|_
    #（ﾟω ｡ 7
    #  |    \
    #  しし__,)ノ
    #cat
