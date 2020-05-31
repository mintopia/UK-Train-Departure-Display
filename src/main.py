import sys
from datetime import datetime
import threading
import time
from pprint import pprint

from luma.core.sprite_system import framerate_regulator

from trains.api import Api
from trains.board import Board
from trains.config import Config

from time import sleep

board = Board()
board.departure_board()

api = Api()
debug = Config.get("debug.stats", False)

frequency = Config.get("debug.frequency", 60)
framerate = Config.get("debug.framerate", 0)
regulator = framerate_regulator(fps=framerate)
timer = None

def minute_timer():
    if not frequency:
        return
    timestamp = datetime.now()
    state = api.get_cached_state(timestamp, frequency, as_dict=True)
    board.update_powersaving(timestamp)
    board.update_state(state)

    global timer
    timer = threading.Timer(frequency + 1, minute_timer)
    timer.start()

minute_timer()

sleep(2)

try:
    while True:
        with regulator:
            timestamp = datetime.now()

            board.update_data(timestamp, regulator.called)

            # Render our board
            board.render(timestamp, regulator.called)

            # Render Stats
            if debug and regulator.called > 0 and regulator.called % 31 == 0:
                avg_fps = regulator.effective_FPS()
                avg_transit_time = regulator.average_transit_time()
            
                sys.stdout.write("#### iter = {0:6d}: render time = {1:.2f} ms, frame rate = {2:.2f} FPS\r".format(regulator.called, avg_transit_time, avg_fps))
                sys.stdout.flush()
except KeyboardInterrupt:
    if timer:
        timer.cancel()
    pass
