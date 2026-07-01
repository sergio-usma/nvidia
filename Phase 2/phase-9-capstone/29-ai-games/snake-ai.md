# Snake AI - Local LLM Plays Snake

This tutorial shows how to create a Snake game where your local AI model controls the snake. Watch the AI navigate and grow the serpent!

## Game Overview

The AI analyzes the game board and decides where to move next to:
- Eat food and grow
- Avoid walls
- Avoid its own body
- Take optimal paths

Features:
- Real-time game visualization
- AI decision streaming (watch it think!)
- System stats monitoring
- Multiple AI backends supported

## Prerequisites

- Python 3.8+
- One of: Ollama, llama.cpp, LMStudio, or MLC-LLM running
- Required packages:

```bash
pip install pygame requests psutil
```

## Project Structure

```
snake-ai/
├── snake_game.py     # Main game logic
├── ai_player.py     # AI decision making
├── stats_monitor.py # Reuse from Tetris
└── config.py        # Configuration
```

## Step 1: Configuration

```python
# config.py

# AI Backend Configuration
AI_BACKEND = "ollama"

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
GRID_SIZE = 20  # 20x20 grid
CELL_SIZE = 25
FPS = 15

# AI Settings
AI_THINK_TIME = 1.5  # Seconds between moves
TEMPERATURE = 0.5    # Lower = more deterministic
```

## Step 2: Reuse Stats Monitor

Copy `stats_monitor.py` from the Tetris project, or create a simplified version:

```python
# stats_monitor.py
import time
import threading
import subprocess

class StatsMonitor:
    def __init__(self, update_interval=1.0):
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.gpu_usage = 0
        self.temperature = 0
        self.memory_used = 0
        self.memory_total = 64
    
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
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total', 
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                values = result.stdout.strip().split(', ')
                self.gpu_usage = int(values[0])
                self.temperature = int(values[1])
                self.memory_used = int(values[2])
                self.memory_total = int(values[3])
        except:
            pass
    
    def get_stats(self):
        return {
            'gpu': self.gpu_usage,
            'temperature': self.temperature,
            'memory_used': self.memory_used,
            'memory_total': self.memory_total,
            'memory_percent': self.memory_used / self.memory_total * 100
        }
```

## Step 3: AI Player for Snake

```python
# ai_player.py
import json
import requests
import time
from config import AI_BACKEND, BACKENDS, TEMPERATURE

class AIAgent:
    def __init__(self, backend=AI_BACKEND):
        self.backend = BACKENDS[backend]
        self.system_prompt = """You are an expert Snake AI player.
Your goal is to eat food, grow longer, and avoid dying.
The snake moves on a grid.

Analyze the current board and decide the BEST direction to move.
Available directions: UP, DOWN, LEFT, RIGHT

IMPORTANT:
- NEVER move into walls
- NEVER move into your own body
- ALWAYS try to eat food when possible
- Take the safest path

Response format (JSON only):
{"direction": "UP/DOWN/LEFT/RIGHT", "reason": "short explanation"}

Choose wisely - one wrong move and you die!"""
    
    def get_direction(self, game_state):
        """Get AI's direction decision"""
        
        user_prompt = self._format_game_state(game_state)
        
        try:
            response = self._call_ai(user_prompt)
            direction = self._parse_response(response)
            return direction
        except Exception as e:
            print(f"AI Error: {e}")
            return self._safe_fallback(game_state)
    
    def _format_game_state(self, state):
        """Format game state for AI"""
        grid = state['grid']
        snake = state['snake']  # List of (y, x) positions
        food = state['food']    # (y, x) position
        
        # Create visual representation
        display = []
        for y in range(len(grid)):
            row = []
            for x in range(len(grid[y])):
                pos = (y, x)
                if pos == food:
                    row.append('F')  # Food
                elif pos in snake:
                    if pos == snake[0]:
                        row.append('H')  # Head
                    else:
                        row.append('S')  # Snake body
                elif grid[y][x] == 1:
                    row.append('#')  # Wall
                else:
                    row.append('.')  # Empty
            display.append(' '.join(row))
        
        grid_str = '\n'.join(display)
        head_y, head_x = snake[0]
        food_y, food_x = food
        
        return f"""Current board:
{grid_str}

Snake head: ({head_y}, {head_x})
Food: ({food_y}, {food_x})
Snake length: {len(snake)}

Where should the snake move?"""
    
    def _call_ai(self, prompt):
        """Call the AI backend"""
        url = f"{self.backend['url']}{self.backend['chat_endpoint']}"
        
        if self.backend['url'] == "http://localhost:11434":
            payload = {
                "model": self.backend['model'],
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"temperature": TEMPERATURE}
            }
        else:
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
        """Parse AI response to get direction"""
        try:
            if '{' in response:
                start = response.find('{')
                end = response.find('}') + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                
                direction = data.get('direction', 'UP').upper()
                valid_directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
                
                if direction in valid_directions:
                    return direction
        except:
            pass
        
        return 'UP'  # Default
    
    def _safe_fallback(self, state):
        """Fallback to simple AI if LLM fails"""
        snake = state['snake']
        food = state['food']
        head = snake[0]
        
        # Simple pathfinding to food
        dy = food[0] - head[0]
        dx = food[1] - head[1]
        
        # Prefer horizontal if closer
        if abs(dx) > abs(dy):
            return 'RIGHT' if dx > 0 else 'LEFT'
        else:
            return 'DOWN' if dy > 0 else 'UP'
```

## Step 4: Main Snake Game

```python
# snake_game.py
import pygame
import random
import time
from config import GRID_SIZE, CELL_SIZE, FPS, AI_THINK_TIME
from ai_player import AIAgent
from stats_monitor import StatsMonitor

class SnakeGame:
    def __init__(self):
        pygame.init()
        
        # Calculate dimensions
        stats_width = 220
        self.width = GRID_SIZE * CELL_SIZE + stats_width
        self.height = GRID_SIZE * CELL_SIZE + 60
        
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Snake AI - Local LLM Playing")
        self.clock = pygame.time.Clock()
        
        # Game state
        self.reset_game()
        
        # AI
        self.ai = AIAgent()
        self.last_ai_time = 0
        self.ai_direction = None
        self.ai_thinking = False
        self.ai_thought = ""
        
        # Stats monitor
        self.stats = StatsMonitor()
        self.stats.start()
        
        # Colors
        self.colors = {
            'background': (20, 25, 30),
            'grid': (35, 40, 50),
            'snake_head': (0, 217, 255),
            'snake_body': (0, 180, 220),
            'food': (255, 80, 80),
            'text': (200, 200, 200),
            'accent': (0, 255, 150),
        }
    
    def reset_game(self):
        """Reset game state"""
        # Start in middle
        start_x = GRID_SIZE // 2
        start_y = GRID_SIZE // 2
        
        self.snake = [(start_y, start_x), (start_y, start_x + 1), (start_y, start_x + 2)]
        self.direction = 'LEFT'
        self.food = self.spawn_food()
        self.score = 0
        self.game_over = False
        self.steps_alive = 0
        
        # Grid (0 = empty, 1 = wall)
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
    
    def spawn_food(self):
        """Spawn food in empty space"""
        while True:
            food = (random.randint(0, GRID_SIZE - 1), 
                   random.randint(0, GRID_SIZE - 1))
            if food not in self.snake:
                return food
    
    def move_snake(self, direction):
        """Move snake in direction"""
        head = self.snake[0]
        
        # Calculate new head position
        if direction == 'UP':
            new_head = (head[0] - 1, head[1])
        elif direction == 'DOWN':
            new_head = (head[0] + 1, head[1])
        elif direction == 'LEFT':
            new_head = (head[0], head[1] - 1)
        elif direction == 'RIGHT':
            new_head = (head[0], head[1] + 1)
        
        # Check collisions
        if (new_head[0] < 0 or new_head[0] >= GRID_SIZE or
            new_head[1] < 0 or new_head[1] >= GRID_SIZE or
            new_head in self.snake):
            self.game_over = True
            return
        
        # Move snake
        self.snake.insert(0, new_head)
        
        # Check food
        if new_head == self.food:
            self.score += 10 + max(0, 50 - self.steps_alive)
            self.food = self.spawn_food()
        else:
            self.snake.pop()
        
        self.steps_alive += 1
    
    def get_game_state(self):
        """Get current game state for AI"""
        return {
            'grid': self.grid,
            'snake': self.snake,
            'food': self.food,
            'direction': self.direction,
            'score': self.score,
            'steps': self.steps_alive
        }
    
    def run(self):
        """Main game loop"""
        running = True
        move_timer = 0
        move_interval = 1000 // FPS
        
        while running:
            current_time = pygame.time.get_ticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.reset_game()
            
            if not self.game_over:
                # AI thinking
                if current_time - self.last_ai_time > AI_THINK_TIME * 1000:
                    self.ai_thinking = True
                    
                    import threading
                    def ai_think():
                        try:
                            state = self.get_game_state()
                            self.ai_direction = self.ai.get_direction(state)
                            self.ai_thought = f"Move: {self.ai_direction}"
                        except Exception as e:
                            self.ai_thought = f"Error: {e}"
                        finally:
                            self.ai_thinking = False
                            self.last_ai_time = current_time
                    
                    thread = threading.Thread(target=ai_think)
                    thread.daemon = True
                    thread.start()
                
                # Execute move
                move_timer += self.clock.get_time()
                if move_timer >= move_interval:
                    move_timer = 0
                    
                    if self.ai_direction:
                        # Validate AI direction doesn't cause immediate death
                        head = self.snake[0]
                        valid = True
                        
                        new_head = head
                        if self.ai_direction == 'UP':
                            new_head = (head[0] - 1, head[1])
                        elif self.ai_direction == 'DOWN':
                            new_head = (head[0] + 1, head[1])
                        elif self.ai_direction == 'LEFT':
                            new_head = (head[0], head[1] - 1)
                        elif self.ai_direction == 'RIGHT':
                            new_head = (head[0], head[1] + 1)
                        
                        # Don't allow 180 degree turns
                        opposite = {
                            'UP': 'DOWN', 'DOWN': 'UP',
                            'LEFT': 'RIGHT', 'RIGHT': 'LEFT'
                        }
                        
                        if opposite.get(self.ai_direction) == self.direction:
                            valid = False
                        
                        # Don't allow death
                        if (new_head in self.snake or
                            new_head[0] < 0 or new_head[0] >= GRID_SIZE or
                            new_head[1] < 0 or new_head[1] >= GRID_SIZE):
                            valid = False
                        
                        if valid:
                            self.direction = self.ai_direction
                    
                    self.move_snake(self.direction)
            
            # Draw
            self.draw()
            self.clock.tick(FPS)
        
        self.stats.stop()
        pygame.quit()
    
    def draw(self):
        """Draw game state"""
        self.screen.fill(self.colors['background'])
        
        # Draw grid
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE - 1, CELL_SIZE - 1)
                pygame.draw.rect(self.screen, self.colors['grid'], rect, 1)
        
        # Draw food
        food_rect = (self.food[1] * CELL_SIZE, self.food[0] * CELL_SIZE, 
                   CELL_SIZE - 1, CELL_SIZE - 1)
        pygame.draw.rect(self.screen, self.colors['food'], food_rect)
        
        # Draw snake
        for i, segment in enumerate(self.snake):
            color = self.colors['snake_head'] if i == 0 else self.colors['snake_body']
            rect = (segment[1] * CELL_SIZE, segment[0] * CELL_SIZE, 
                   CELL_SIZE - 1, CELL_SIZE - 1)
            pygame.draw.rect(self.screen, color, rect)
        
        # Draw stats panel
        self.draw_stats()
        
        # Game over overlay
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            
            font = pygame.font.Font(None, 48)
            text = font.render("GAME OVER", True, (255, 80, 80))
            self.screen.blit(text, (self.width // 2 - 100, self.height // 2 - 30))
            
            font = pygame.font.Font(None, 24)
            score_text = font.render(f"Final Score: {self.score}", True, (255, 255, 255))
            self.screen.blit(score_text, (self.width // 2 - 70, self.height // 2 + 10))
            
            restart_text = font.render("Press R to Restart", True, (200, 200, 200))
            self.screen.blit(restart_text, (self.width // 2 - 80, self.height // 2 + 40))
        
        pygame.display.flip()
    
    def draw_stats(self):
        """Draw stats panel"""
        x_offset = GRID_SIZE * CELL_SIZE + 10
        
        # Title
        font = pygame.font.Font(None, 22)
        title = font.render("AI Snake Stats", True, self.colors['accent'])
        self.screen.blit(title, (x_offset, 10))
        
        # Get stats
        stats = self.stats.get_stats()
        
        y = 45
        font = pygame.font.Font(None, 18)
        
        # Game stats
        stats_text = [
            f"Score: {self.score}",
            f"Length: {len(self.snake)}",
            f"Steps: {self.steps_alive}",
            "",
            "--- System ---",
            f"GPU: {stats['gpu']}%",
            f"Memory: {stats['memory_percent']:.0f}%",
            f"Temp: {stats['temperature']}°C" if stats['temperature'] else "Temp: N/A",
            "",
            "--- AI ---",
        ]
        
        for line in stats_text:
            text = font.render(line, True, self.colors['text'])
            self.screen.blit(text, (x_offset, y))
            y += 18
        
        # AI status
        if self.ai_thinking:
            color = (0, 255, 100)
            status = "Thinking..."
        elif self.ai_thought:
            color = (255, 220, 0)
            status = self.ai_thought[:25]
        else:
            color = (120, 120, 120)
            status = "Ready"
        
        text = font.render(status, True, color)
        self.screen.blit(text, (x_offset, y + 10))

if __name__ == "__main__":
    game = SnakeGame()
    game.run()
```

## Step 5: Run the Game

```bash
# Make sure your AI backend is running
# For Ollama:
# docker exec ollama ollama serve

# Run the game
cd snake-ai
python snake_game.py
```

## AI Strategies

Try modifying the system prompt in `ai_player.py` for different behaviors:

### Survival Mode
```python
self.system_prompt = """You are a survival-focused Snake AI.
Your ONLY priority is to stay alive.
Don't take risks.
Play as long as possible.
Respond with JSON: {"direction": "UP/DOWN/LEFT/RIGHT"}"""
```

### Aggressive Mode
```python
self.system_prompt = """You are an aggressive Snake AI.
Go for food ASAP.
Take calculated risks.
Speed is life.
Respond with JSON: {"direction": "UP/DOWN/LEFT/RIGHT"}"""
```

### Perfect Mode
```python
self.system_prompt = """You are a perfect Snake AI.
Always find the optimal path.
Use BFS-like thinking.
Never die if possible.
Respond with JSON: {"direction": "UP/DOWN/LEFT/RIGHT"}"""
```

## Comparing Models

Test different local models to see which plays best:

| Model | Strengths | Weaknesses |
|-------|-----------|------------|
| llama3.2 | Fast decisions | May take risks |
| mistral | Balanced play | Can get trapped |
| qwen2.5 | Good planning | Sometimes slow |
| tinyllama | Very fast | Simple strategies |

## Performance Tips

1. **Use smaller models** for faster response times
2. **Lower temperature** for more consistent play
3. **Adjust AI_THINK_TIME** if game feels too slow
4. **Monitor GPU** with jtop to see AI processing load

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Snake dies instantly | Check direction validation code |
| AI too slow | Use smaller model or reduce think time |
| Game lag | Reduce FPS in config |
| No GPU stats | Install nvidia-smi |

## Next Steps

- Customize the AI prompts for different personalities
- Add multiple AIs competing
- Create a leaderboard
- Add obstacles for extra challenge
