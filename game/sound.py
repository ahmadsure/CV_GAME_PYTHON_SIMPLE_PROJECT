"""Optional sound effects. Needs `pip install pygame`; silently disabled if unavailable."""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_DIR = os.path.join(ROOT, "assets", "sounds")
ALIASES = {"start": "slice"}


class SoundBank:
    def __init__(self, folder=SOUND_DIR, enabled=True):
        self.sounds = {}
        if not enabled:
            return
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)
            for path in glob.glob(os.path.join(folder, "*.wav")):
                self.sounds[os.path.splitext(os.path.basename(path))[0]] = pygame.mixer.Sound(path)
        except Exception as e:                     # no pygame / no audio device
            print(f"[sound] disabled ({e}). Install pygame for sound: pip install pygame")

    def play(self, name):
        s = self.sounds.get(ALIASES.get(name, name))
        if s is not None:
            s.play()
