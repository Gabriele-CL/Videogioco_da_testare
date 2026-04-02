import subprocess
import sys


def install(pkg):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", pkg],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


try:
    import pygame
except ImportError:
    install("pygame")
    import pygame
