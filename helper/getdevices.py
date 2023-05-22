import pygame as pg
import time

from pygame._sdl2 import (
    get_audio_device_names,
    AudioDevice,
    AUDIO_F32,
    AUDIO_ALLOW_FORMAT_CHANGE,
)
from pygame._sdl2.mixer import set_post_mix

pg.mixer.pre_init(44100, 32, 2, 512)
pg.init()

# init_subsystem(INIT_AUDIO)
names = get_audio_device_names(True)
print(names)