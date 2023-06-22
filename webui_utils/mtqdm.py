"""Multiple TQDM progress bar manager singleton class"""
from tqdm import tqdm
from contextlib import contextmanager

class Mtqdm:
    """Manage N nested tqdm progress bars with auto-coloring"""
    def __new__(cls, palette : str="default"):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Mtqdm, cls).__new__(cls)
            cls.instance.init(palette)
        return cls.instance

    MAX_BARS = 9

    def init(self, palette : str="default"):
        self.current_palette = Mtqdm.palettes[palette]
        self.entered_bars = [None for n in range(Mtqdm.MAX_BARS)]
        self.bar_totals = [0 for n in range(Mtqdm.MAX_BARS)]
        self.position = -1
        self.color = -1
        self.leave = -1

    colors = {
        "red" : "#FF0000",
        "orange" : "#FF7F00",
        "yellow" : "#FFFF00",
        "green" : "#00FF00",
        "blue" : "#0000FF",
        "purple" : "#7F00FF",
        "cyan" : "#00FFFF",
        "magenta" : "#FF00FF",
        "white" : "#FFFFFF"}

    default_palette = [
        colors["green"],
        colors["yellow"],
        colors["orange"],
        colors["red"],
        colors["blue"],
        colors["purple"],
        colors["magenta"],
        colors["cyan"],
        colors["white"]]

    rainbow_palette = [
        colors["red"],
        colors["orange"],
        colors["yellow"],
        colors["green"],
        colors["blue"],
        colors["purple"],
        colors["magenta"],
        colors["cyan"],
        colors["white"]]

    palettes = {
        "default" : default_palette,
        "rainbow" : rainbow_palette
    }

    def get_position(self):
        return self.position

    def enter_position(self):
        self.position += 1
        return self.get_position()

    def leave_position(self):
        self.position -= 1

    def get_color(self):
        return self.current_palette[self.color]

    def enter_color(self):
        self.color += 1
        return self.get_color()

    def leave_color(self):
        self.color -= 1

    def get_leave(self):
        return self.leave == 0

    def enter_leave(self):
        self.leave += 1
        return self.get_leave()

    def leave_leave(self):
        self.leave -= 1

    def find_bar_position(self, bar):
        try:
            return self.entered_bars.index(bar)
        except ValueError:
            return None

    def enter_bar(self, total=100, desc="Please Wait"):
        position = self.enter_position()
        leave = self.enter_leave()
        color = self.enter_color()
        bar = tqdm(total=total, desc=desc, position=position, leave=leave, colour=color)
        self.entered_bars[position] = bar
        self.bar_totals[position] = total
        return bar

    def leave_bar(self, bar):
        position = self.find_bar_position(bar)
        if position != None:

            # current_position = get_position()
            # if position < current_position:
            #     deeper_bar = entered_bars(position+1)
            #     leave_bar(deeper_bar)
            #     return

            self.leave_color()
            self.leave_leave()
            self.leave_position()
            bar.close()
            self.entered_bars[position] = None

            # now_current_position = get_position()
            # now_current_bar = entered_bars[now_current_position]
            # now_current_bar.update()

    @contextmanager
    def open_bar(self, total=100, desc="Please Wait"):
        try:
            bar = self.enter_bar(total=total, desc=desc)
            yield bar
        finally:
            self.leave_bar(bar)

    def update_bar(self, bar, steps=1):
        bar.update(n=steps)

    def get_bar(self, index):
        return self.entered_bars[index]

    def get_bar_max(self, index):
        return self.bar_totals[index]

import time
import random

class MtqdmTester():
    # mtqdm = Mtqdm()
    indexes = []
    bars = []

    def make_bar(self, bar_num, max):
        return MtqdmTester.mtqdm.enter_bar(total=max, desc=f"Bar{bar_num}")

    def test_bars_1(self, number_of_bars, number_of_steps, delay):
        MtqdmTester.indexes = [0 for n in range(number_of_bars)]
        MtqdmTester.bars = [self.make_bar(n, number_of_steps) for n in range(number_of_bars)]

        for n in range(1, 10000):
            keep_going = self.advance_indexes()
            if keep_going:
                time.sleep(delay)
                continue
            else:
                break

        for bar in reversed(MtqdmTester.bars):
            MtqdmTester.mtqdm.leave_bar(bar)

    def optional_process(self, min, max, delay):
        count = random.randint(min, max)
        with Mtqdm().open_bar(desc="Optional Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                Mtqdm().update_bar(bar)

    def deep_process(self, min, max, delay):
        count = random.randint(min, max)
        with Mtqdm().open_bar(desc="Deep Process", total=count) as bar:
            for n in range(count):
                if count % min == 0:
                    self.optional_process(min, max, delay)
                time.sleep(delay)
                Mtqdm().update_bar(bar)

    def shallow_process(self, min, max, delay):
        count = random.randint(min, max)
        with Mtqdm().open_bar(desc="Shallow Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                self.deep_process(min, max, delay)
                Mtqdm().update_bar(bar)

    def main_process(self, min, max, delay):
        count = random.randint(min, max)
        with Mtqdm().open_bar(desc="Main Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                self.shallow_process(min, max, delay)
                Mtqdm().update_bar(bar)

    def test_bars_2(self, min, max, delay):
        self.main_process(min, max, delay)

    def advance_index(self, index):
        global indexes, bars
        value = MtqdmTester.indexes[index]
        max = Mtqdm().get_bar_max(index)
        if index == 0 and value == max-1:
            MtqdmTester.bars[index].update()
            return False

        if value == max-1:
            MtqdmTester.indexes[index] = 0
            MtqdmTester.bars[index].reset()
            MtqdmTester.bars[index].refresh()
            return self.advance_index(index-1)
        else:
            MtqdmTester.indexes[index] = value + 1
            MtqdmTester.bars[index].update()
            return True

    def advance_indexes(self):
        global indexes
        last_index = len(MtqdmTester.indexes)-1
        return self.advance_index(last_index)

def main():
    #MtqdmTester().test_bars_1(5, 10, 0.000000001)
    MtqdmTester().test_bars_2(5, 15, 0.1)

if __name__ == '__main__':
    main()
