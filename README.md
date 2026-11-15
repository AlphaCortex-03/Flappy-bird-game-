# Flappy Bird 🐤

A Flappy Bird clone I wrote in Python with Pygame. No image files, no sound files — every sprite (the bird, pipes, clouds, ground) is drawn with code, so the whole game is just a single `main.py`.

## How to Run

Make sure you have **Python 3.8+** installed, then:

```bash
pip install -r requirements.txt
python main.py
```

That's it. The game opens in a 400x600 window.

## How to Play

| Key / Action | What it does |
|---|---|
| `SPACE` / `UP ARROW` / Mouse Click | Flap |
| `P` | Pause / Resume |
| `R` | Restart after Game Over |

Tap to flap, thread the bird through the pipe gaps, and don't hit anything. Every pipe you pass is 1 point, and the pipes scroll a little faster every 5 points — so it only gets harder the longer you survive.

Your best score is saved to `best_score.txt` next to the game, so it sticks between runs. The file is created automatically, no need to make it yourself.

## Features

- Classic one-button gameplay (space / click to flap)
- Best score is saved locally and shown on the start screen
- Gradual difficulty — pipes speed up every 5 points
- Scrolling clouds and ground for that extra bit of life
- Pause screen, game over screen, everything drawn with Pygame primitives

## Requirements

Only dependency is **pygame** (see `requirements.txt`):

```
pygame
```

## Project Structure

```
Flappy Bird/
├── main.py           # the whole game
├── requirements.txt  # pygame
├── best_score.txt    # created automatically, stores your best score
└── README.md
```

## License

Free to use, modify and share — have fun with it. 🎮
