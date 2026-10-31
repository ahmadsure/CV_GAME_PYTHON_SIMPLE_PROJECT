# Fruit Slash

Slice fruit in mid-air with your finger. Webcam + MediaPipe hand tracking + OpenCV rendering.

## Run

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                  # webcam + hand tracking
python main.py --mouse          # no camera: the mouse is the blade (good for testing)
```

First run downloads the MediaPipe hand model (~8 MB) into `assets/models/`
(only needed on MediaPipe versions that dropped the old `mp.solutions` API; handled automatically).
If you are offline, download it manually from the URL printed in the error and save it at the printed path.

Sound needs `pygame` (in requirements.txt); run with `--no-sound` to disable.

**Keys:** `q`/`Esc` quit · `h` show hand skeleton · `r` restart · `f` fullscreen

**How to play:** slice the watermelon to start. Swipe your index finger *fast* through fruit.
Missing a fruit costs a life (3 lives). Bombs end the game. Slicing 2+ fruit in one swipe gives a combo bonus.
Stand ~1 m from the camera with good front lighting and keep your hand inside the frame.

## How it works

```
camera thread ─► mirror ─► HandTracker (MediaPipe, index fingertip = landmark 8)
                                │
                          SwipeDetector  – smooths the tip, tracks each hand, emits a blade
                                │          segment (prev → now) only when the tip moves fast enough
                              Game       – physics, segment-vs-circle hit test, scoring, lives
                                │
              sprites ─► cut_sprite() splits a fruit along the blade angle into two halves
                                │
                      Effects (juice, splats, popups, blade trail) ─► OpenCV window
```

| File | Job |
|---|---|
| `game/tracker.py` | MediaPipe wrapper (legacy + Tasks API), mouse fallback |
| `game/swipe.py` | fingertip → fast-swipe blade segments |
| `game/engine.py` | spawning, gravity, slicing, scoring, HUD |
| `game/assets.py` | sprites (procedural or real PNGs), sprite rotation, **cut-in-half** |
| `game/effects.py` | juice particles, splats, blade trail, text |
| `game/camera.py` | threaded webcam capture |
| `game/sound.py` | optional sound effects (pygame) |
| `tools/make_assets.py` | writes all PNG / WAV assets |
| `tests/smoke_test.py` | headless bot that plays the game and writes preview PNGs |

Why a segment and not a point? The camera runs at ~30 fps, so a fast swipe jumps 100+ px per frame.
Testing the whole segment between two frames against each fruit circle means nothing slips through.

## Assets (already included)

```
assets/fruits/   apple, kiwi, lemon, lime, orange, peach, strawberry, watermelon, bomb  (240x240 transparent PNG)
assets/cut/      the INSIDE of each fruit - shown on the two halves after a cut
assets/sounds/   slice, combo, bomb, miss, over  (.wav)
```

Regenerate everything any time with `python tools/make_assets.py`.
Preview the cut animation frame-by-frame: `python tests/cut_preview.py out.png`.

**The cut animation:** blade crosses fruit → white slash flash along the cut line → the fruit is replaced by two
half-sprites that show its inside (`assets/cut/<name>.png`), each pushed away from the cut line, spinning and
falling under gravity, with juice particles and a splat on the background.

## Use your own REAL fruit photos

Put transparent-background PNGs in `assets/fruits/` (same name = replace, new name = new fruit):

```
assets/fruits/apple.png      # replaces the built-in apple
assets/fruits/banana.png     # new fruit, added to the pool
assets/fruits/bomb.png       # replaces the bomb
```

Non-240x240 images are auto-cropped, scaled and centred. To get real-looking halves, also add the inside
of the fruit (a photo of the cut face, transparent background) as `assets/cut/<same name>.png`.
**If you replace a built-in fruit with a photo, delete its `assets/cut/<name>.png`** (or replace it too),
otherwise the halves show the cartoon inside. With no cut image the game cuts your photo along the blade
and paints a flesh-coloured edge, which works for any fruit. New names derive juice colour from the photo.
Tip: remove photo backgrounds with `pip install rembg` → `rembg i in.jpg out.png`.

## Tuning

| Flag / constant | Effect |
|---|---|
| `--min-speed 0.6` | easier cuts (lower = slower swipes count). Default 0.9 screen-widths/sec |
| `--smooth 0.8` | snappier blade, more jitter. Default 0.65 |
| `GRAVITY` in `engine.py` | floaty vs heavy fruit |
| `_spawn_wave` in `engine.py` | difficulty curve, bomb frequency |
| `HandTracker(proc_width=...)` | smaller = faster tracking, larger = more accurate |

## Ideas for next steps

- Sound: `pygame.mixer` for slice / bomb / combo sounds
- Slow-motion on combos (scale `dt`), power-ups (freeze, double points), banana-style fruit with elongated hit shapes
- Both hands as separate blades already works (up to 2 tracked hands)
- One-Euro filter instead of the simple smoothing for steadier fingertips
- High-score file, difficulty modes, two-player split screen
