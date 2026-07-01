# Tetris AI - Local LLM Plays Tetris

This tutorial shows how to create a Tetris game where your local AI model plays the game. Watch your Jetson's AI think and make decisions in real-time!

## Game Overview

The AI analyzes the game state and decides which move to make next. You'll see:
- Real-time game visualization
- AI decision-making process
- System stats (GPU, memory, temperature)
- Move history and scoring

## Prerequisites

- Python 3.8+
- One of: Ollama, llama.cpp, LMStudio, or MLC-LLM running
- Required packages:

```bash
pip install pygame requests pynvml
```

## Project Structure

```
tetris-ai/
├── tetris_game.py     # Main game logic
├── ai_player.py       # AI decision making
├── stats_monitor.py   # System monitoring
└── config.py          # Configuration
```

## Step 1: Create Configuration File

```python
# config.py

# AI Backend Configuration
AI_BACKEND = "ollama"  # Options: ollama, llamacpp, lmstudio, mlc

# Backend URLs
BACKENDS = {
    "ollama": {
        "url": "http://localhost:11434",
        "chat_endpoint": "/api/chat",
        "model": "llama3.2"
    },
    "llamacpp": {
        "url": "http://localhost:8080",
        "chat_endpoint": "/v1/chat/completions",
        "model": "local-model"
    },
    "lmstudio": {
        "url": "http://localhost:1234",
        "chat_endpoint": "/v1/chat/completions",
        "model": "local-model"
    },
    "mlc": {
        "url": "http://localhost:8000",
        "chat_endpoint": "/v1/chat/completions",
        "model": "local-model"
    }
}

# Game Settings
GAME_WIDTH = 10
GAME_HEIGHT = 20
BLOCK_SIZE = 30
FPS = 60

# AI Settings
AI_THINK_TIME = 2.0  # Seconds to wait for AI response
TEMPERATURE = 0.7    # AI creativity (0.0 - 1.0)

# System Monitoring
MONITOR_STATS = True
STATS_UPDATE_INTERVAL = 1.0
```

## Step 2: Create System Stats Monitor

```python
# stats_monitor.py
import time
import threading
import requests
from collections import deque

class StatsMonitor:
    def __init__(self, update_interval=1.0):
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        
        # Stats storage
        self.gpu_usage = 0
        self.memory_used = 0
        self.memory_total = 64
        self.temperature = 0
        self.cpu_usage = 0
        
        # History for graphing
        self.history_length = 60
        self.gpu_history = deque(maxlen=60)
        self.memory_history = deque(maxlen=60)
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _monitor_loop(self):
        while self.running:
            self._update_stats()
            time.sleep(self.update_interval)
    
    def _update_stats(self):
        try:
            # Try nvidia-smi first
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', 
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                values = result.stdout.strip().split(', ')
                self.gpu_usage = int(values[0])
                self.memory_used = int(values[1])
                self.memory_total = int(values[2])
                self.temperature = int(values[3])
            else:
                self._fallback_stats()
        except:
            self._fallback_stats()
        
        # Update history
        self.gpu_history.append(self.gpu_usage)
        self.memory_history.append(self.memory_used / self.memory_total * 100)
    
    def _fallback_stats(self):
        import psutil
        self.cpu_usage = psutil.cpu_percent()
        import os
        mem = psutil.virtual_memory()
        self.memory_used = mem.used / (1024**3)
        self.memory_total = mem.total / (1024**3)
    
    def get_stats(self):
        return {
            'gpu': self.gpu_usage,
            'memory_used': self.memory_used,
            'memory_total': self.memory_total,
            'memory_percent': self.memory_used / self.memory_total * 100,
            'temperature': self.temperature,
            'cpu': self.cpu_usage
        }
```

## Step 3: Create AI Player Module

```python
# ai_player.py
import json
import requests
import time
from config import AI_BACKEND, BACKENDS, TEMPERATURE

class AIPlayer:
    def __init__(self, backend=AI_BACKEND):
        self.backend = BACKENDS[backend]
        self.system_prompt = """You are an expert Tetris player. 
Analyze the current game state and recommend the best move.
Consider:
1. Clearing lines
2. Avoiding gaps
3. Keeping pieces low
4. Creating opportunities for line clears

Respond with ONLY a JSON object in this format:
{"action": "left/right/rotate/drop/fast_drop", "moves": number_of_moves}

For rotation, use "rotate" and specify moves (1-3).
For drop, use "drop" for soft drop or "fast_drop" for hard drop."""

    def get_move(self, game_state):
        """Get AI's move based on current game state"""
        
        # Prepare prompt with game state
        user_prompt = self._format_game_state(game_state)
        
        try:
            response = self._call_ai(user_prompt)
            move = self._parse_response(response)
            return move
        except Exception as e:
            print(f"AI Error: {e}")
            return 'drop', 1  # Default to drop
    
    def _format_game_state(self, game_state):
        """Format game state for AI"""
        grid = game_state['grid']
        current_piece = game_state['current_piece']
        next_piece = game_state.get('next_piece', '?')
        
        # Create text representation
        grid_str = "\n".join(["".join(row) for row in grid])
        
        return f"""Current game state:
Grid (0=empty, 1=filled):
{grid_str}

Current piece: {current_piece}
Next piece: {next_piece}

What move should I make?"""
    
    def _call_ai(self, prompt):
        """Call the AI backend"""
        url = f"{self.backend['url']}{self.backend['chat_endpoint']}"
        
        if self.backend['url'] == "http://localhost:11434":
            # Ollama format
            payload = {
                "model": self.backend['model'],
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": TEMPERATURE
                }
            }
        else:
            # OpenAI-compatible format
            payload = {
                "model": self.backend['model'],
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": TEMPERATURE
            }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        if self.backend['url'] == "http://localhost:11434":
            return response.json()['message']['content']
        else:
            return response.json()['choices'][0]['message']['content']
    
    def _parse_response(self, response):
        """Parse AI response to get move"""
        try:
            # Try to extract JSON from response
            if '{' in response:
                start = response.find('{')
                end = response.find('}') + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                
                action = data.get('action', 'drop')
                moves = int(data.get('moves', 1))
                
                return action, moves
        except:
            pass
        
        # Default fallback
        return 'drop', 1
```

## Step 4: Create Main Tetris Game

```python
# tetris_game.py
import pygame
import random
import time
from config import GAME_WIDTH, GAME_HEIGHT, BLOCK_SIZE, FPS, AI_THINK_TIME
from ai_player import AIPlayer
from stats_monitor import StatsMonitor

# Tetris pieces
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 1], [1, 0, 0]],  # L
    [[1, 1, 1], [0, 0, 1]],  # J
    [[1, 1, 0], [0, 1, 1]],  # S
    [[0, 1, 1], [1, 1, 0]],  # Z
]

COLORS = [
    (0, 255, 255),  # I - Cyan
    (255, 255, 0),  # O - Yellow
    (128, 0, 128),  # T - Purple
    (255, 165, 0),  # L - Orange
    (0, 0, 255),    # J - Blue
    (0, 255, 0),    # S - Green
    (255, 0, 0),     # Z - Red
]

class TetrisGame:
    def __init__(self):
        pygame.init()
        
        # Calculate dimensions
        stats_width = 250
        self.width = GAME_WIDTH * BLOCK_SIZE + stats_width
        self.height = GAME_HEIGHT * BLOCK_SIZE + 50
        
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tetris AI - Local LLM Playing")
        self.clock = pygame.time.Clock()
        
        # Game state
        self.grid = [[0] * GAME_WIDTH for _ in range(GAME_HEIGHT)]
        self.current_piece = None
        self.current_color = None
        self.piece_pos = [0, 0]
        self.next_piece = None
        self.next_color = None
        self.score = 0
        self.lines_cleared = 0
        self.game_over = False
        self.paused = False
        
        # AI
        self.ai_player = AIPlayer()
        self.ai_thinking = False
        self.ai_move = None
        self.last_ai_move_time = 0
        self.ai_thought = ""
        
        # Stats monitor
        self.stats = StatsMonitor()
        self.stats.start()
        
        # Spawn first piece
        self.spawn_piece()
    
    def spawn_piece(self):
        """Spawn a new piece"""
        idx = random.randint(0, len(SHAPES) - 1)
        self.current_piece = SHAPES[idx]
        self.current_color = COLORS[idx]
        self.piece_pos = [0, GAME_WIDTH // 2 - len(self.current_piece[0]) // 2]
        
        # Check game over
        if self.check_collision(self.piece_pos, self.current_piece):
            self.game_over = True
    
    def check_collision(self, pos, piece):
        """Check if piece collides with grid or walls"""
        for y, row in enumerate(piece):
            for x, cell in enumerate(row):
                if cell:
                    new_x = pos[1] + x
                    new_y = pos[0] + y
                    if new_x < 0 or new_x >= GAME_WIDTH:
                        return True
                    if new_y >= GAME_HEIGHT:
                        return True
                    if new_y >= 0 and self.grid[new_y][new_x]:
                        return True
        return False
    
    def rotate_piece(self):
        """Rotate current piece"""
        rotated = list(zip(*self.current_piece[::-1]))
        if not self.check_collision(self.piece_pos, rotated):
            self.current_piece = rotated
    
    def move_piece(self, dx):
        """Move piece left/right"""
        if not self.check_collision([self.piece_pos[0], self.piece_pos[1] + dx], self.current_piece):
            self.piece_pos[1] += dx
    
    def drop_piece(self):
        """Drop piece one step"""
        if not self.check_collision([self.piece_pos[0] + 1, self.piece_pos[1]], self.current_piece):
            self.piece_pos[0] += 1
            return True
        else:
            # Lock piece
            self.lock_piece()
            return False
    
    def fast_drop(self):
        """Drop piece all the way down"""
        while self.drop_piece():
            pass
    
    def lock_piece(self):
        """Lock piece into grid"""
        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell:
                    new_x = self.piece_pos[1] + x
                    new_y = self.piece_pos[0] + y
                    if 0 <= new_y < GAME_HEIGHT and 0 <= new_x < GAME_WIDTH:
                        self.grid[new_y][new_x] = self.current_color
        
        # Clear lines
        self.clear_lines()
        
        # Spawn new piece
        self.spawn_piece()
    
    def clear_lines(self):
        """Clear completed lines"""
        lines = 0
        for y in range(GAME_HEIGHT):
            if all(self.grid[y]):
                lines += 1
                self.grid.pop(y)
                self.grid.insert(0, [0] * GAME_WIDTH)
        
        if lines > 0:
            self.score += [0, 100, 300, 500, 800][lines] * lines
            self.lines_cleared += lines
    
    def get_game_state(self):
        """Get current game state for AI"""
        # Convert grid to string format
        grid_str = []
        for y in range(GAME_HEIGHT):
            row = []
            for x in range(GAME_WIDTH):
                if self.grid[y][x]:
                    row.append('1')
                else:
                    row.append('0')
            grid_str.append(row)
        
        # Get piece name
        piece_names = ['I', 'O', 'T', 'L', 'J', 'S', 'Z']
        idx = SHAPES.index(self.current_piece) if self.current_piece in SHAPES else 0
        
        return {
            'grid': grid_str,
            'current_piece': piece_names[idx],
            'next_piece': piece_names[random.randint(0, 6)] if self.next_piece else '?',
            'score': self.score,
            'lines': self.lines_cleared
        }
    
    def execute_ai_move(self):
        """Execute AI's decision"""
        if not self.ai_move:
            return
        
        action, moves = self.ai_move
        
        if action == 'left':
            for _ in range(moves):
                self.move_piece(-1)
        elif action == 'right':
            for _ in range(moves):
                self.move_piece(1)
        elif action == 'rotate':
            for _ in range(moves):
                self.rotate_piece()
        elif action == 'drop':
            for _ in range(moves):
                self.drop_piece()
        elif action == 'fast_drop':
            self.fast_drop()
        
        self.ai_move = None
    
    def run(self):
        """Main game loop"""
        running = True
        drop_timer = 0
        drop_interval = 500  # ms between drops
        
        while running:
            current_time = pygame.time.get_ticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.__init__()  # Restart
            
            if not self.paused and not self.game_over:
                # Auto drop
                drop_timer += self.clock.get_time()
                if drop_timer >= drop_interval:
                    drop_timer = 0
                    self.drop_piece()
                
                # AI thinking
                if not self.ai_thinking and current_time - self.last_ai_move_time > AI_THINK_TIME * 1000:
                    self.ai_thinking = True
                    game_state = self.get_game_state()
                    
                    # Get AI move in separate thread would be better
                    # For simplicity, we do it here with timeout
                    import threading
                    
                    def ai_think():
                        try:
                            self.ai_move = self.ai_player.get_move(game_state)
                            self.ai_thought = f"Move: {self.ai_move}"
                        except Exception as e:
                            self.ai_thought = f"Error: {e}"
                        finally:
                            self.ai_thinking = False
                            self.last_ai_move_time = current_time
                    
                    thread = threading.Thread(target=ai_think)
                    thread.daemon = True
                    thread.start()
                
                # Execute AI move
                if self.ai_move:
                    self.execute_ai_move()
            
            # Draw
            self.draw()
            self.clock.tick(FPS)
        
        self.stats.stop()
        pygame.quit()
    
    def draw(self):
        """Draw game state"""
        self.screen.fill((20, 20, 30))
        
        # Draw game grid
        for y in range(GAME_HEIGHT):
            for x in range(GAME_WIDTH):
                if self.grid[y][x]:
                    pygame.draw.rect(
                        self.screen, 
                        self.grid[y][x],
                        (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE - 1, BLOCK_SIZE - 1)
                    )
        
        # Draw current piece
        if self.current_piece:
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(
                            self.screen,
                            self.current_color,
                            ((self.piece_pos[1] + x) * BLOCK_SIZE,
                             (self.piece_pos[0] + y) * BLOCK_SIZE,
                             BLOCK_SIZE - 1, BLOCK_SIZE - 1)
                        )
        
        # Draw grid lines
        for x in range(GAME_WIDTH + 1):
            pygame.draw.line(self.screen, (50, 50, 50),
                           (x * BLOCK_SIZE, 0), (x * BLOCK_SIZE, GAME_HEIGHT * BLOCK_SIZE))
        for y in range(GAME_HEIGHT + 1):
            pygame.draw.line(self.screen, (50, 50, 50),
                           (0, y * BLOCK_SIZE), (GAME_WIDTH * BLOCK_SIZE, y * BLOCK_SIZE))
        
        # Draw stats panel
        self.draw_stats()
        
        # Draw game over
        if self.game_over:
            font = pygame.font.Font(None, 48)
            text = font.render("GAME OVER", True, (255, 0, 0))
            self.screen.blit(text, (self.width // 2 - 100, self.height // 2))
        
        pygame.display.flip()
    
    def draw_stats(self):
        """Draw stats panel"""
        x_offset = GAME_WIDTH * BLOCK_SIZE + 10
        
        # Get stats
        stats = self.stats.get_stats()
        
        # Title
        font = pygame.font.Font(None, 24)
        title = font.render("AI Tetris Stats", True, (0, 217, 255))
        self.screen.blit(title, (x_offset, 10))
        
        # Game stats
        y = 50
        font = pygame.font.Font(None, 20)
        
        stats_text = [
            f"Score: {self.score}",
            f"Lines: {self.lines_cleared}",
            "",
            "--- System ---",
            f"GPU: {stats['gpu']}%",
            f"Memory: {stats['memory_percent']:.1f}%",
            f"Temp: {stats['temperature']}°C" if stats['temperature'] else "Temp: N/A",
            "",
            "--- AI Status ---",
        ]
        
        for line in stats_text:
            text = font.render(line, True, (200, 200, 200))
            self.screen.blit(text, (x_offset, y))
            y += 20
        
        # AI thinking indicator
        if self.ai_thinking:
            color = (0, 255, 0)
            text = font.render("AI Thinking...", True, color)
        elif self.ai_thought:
            color = (255, 255, 0)
            text = font.render(self.ai_thought[:30], True, color)
        else:
            text = font.render("Ready", True, (100, 100, 100))
        
        self.screen.blit(text, (x_offset, y + 20))

if __name__ == "__main__":
    game = TetrisGame()
    game.run()
```

## Step 5: Run the Game

```bash
# Make sure your AI backend is running
# For Ollama:
# docker exec ollama ollama serve

# Run the game
cd tetris-ai
python tetris_game.py
```

## Customizing AI Behavior

Edit the `system_prompt` in `ai_player.py` to change AI behavior:

```python
# Strategic AI
self.system_prompt = """You are a strategic Tetris player.
Prioritize:
1. Keep the board even
2. Build for future tetris
3. Avoid creating holes
Respond with JSON."""

# Aggressive AI  
self.system_prompt = """You are an aggressive Tetris player.
Go for quick line clears.
Risk is okay for speed.
Respond with JSON."""

# Defensive AI
self.system_prompt = """You are a defensive Tetris player.
Never create holes.
Build carefully and steadily.
Respond with JSON."""
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| AI not responding | Check backend URL in config.py |
| Game runs slow | Reduce FPS in config.py |
| Out of memory | Use smaller model or reduce AI thinking frequency |
| No GPU stats | Install nvidia-smi or use psutil fallback |

## Next Steps

- Try [Snake AI](snake-ai.md) - Another classic game!
- Experiment with different models
- Add more AI personalities
- Create a tournament between AIs
