"""Multiple TQDM progress bar manager singleton class"""
import random
from tqdm import tqdm
from contextlib import contextmanager

class Mtqdm:
    """Manage N nested tqdm progress bars with auto-coloring"""
    def __new__(cls, use_color : bool=True, palette : str="default"):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Mtqdm, cls).__new__(cls)
            cls.instance.init(use_color, palette)
        return cls.instance

    MAX_BARS = 9
    MAX_COLORS = MAX_BARS

    def init(self, use_color : bool=True, palette : str="default"):
        self.use_color = use_color
        self.current_palette = palette
        self.entered_bars = [None for n in range(Mtqdm.MAX_BARS)]
        self.bar_totals = [0 for n in range(Mtqdm.MAX_BARS)]
        self.entered_count = 0
        self.position = -1
        self.color = -1
        self.leave = -1
        self.alternation = True

    colors = {
        "red" : "#AF0000",
        "orange" : "#AF5F00",
        "yellow" : "#AFAF00",
        "green" : "#00AF00",
        "blue" : "#0000AF",
        "purple" : "#5F00AF",
        "cyan" : "#00AFAF",
        "magenta" : "#AF00AF",
        "white" : "#AFAFAF"}

    alt_colors = {
        "red" : "#9F0000",
        "orange" : "#9F5700",
        "yellow" : "#9FAF00",
        "green" : "#009F00",
        "blue" : "#0000AF",
        "purple" : "#57009F",
        "cyan" : "#009F9F",
        "magenta" : "#9F009F",
        "white" : "#9F9F9F"}

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

    default_palette_alt = [
        alt_colors["green"],
        alt_colors["yellow"],
        alt_colors["orange"],
        alt_colors["red"],
        alt_colors["blue"],
        alt_colors["purple"],
        alt_colors["magenta"],
        alt_colors["cyan"],
        alt_colors["white"]]

    rainbow_palette_alt = [
        alt_colors["red"],
        alt_colors["orange"],
        alt_colors["yellow"],
        alt_colors["green"],
        alt_colors["blue"],
        alt_colors["purple"],
        alt_colors["magenta"],
        alt_colors["cyan"],
        alt_colors["white"]]

    palettes = {
        "default" : default_palette,
        "rainbow" : rainbow_palette,
        "random" : default_palette
    }

    alt_palettes = {
        "default" : default_palette_alt,
        "rainbow" : rainbow_palette_alt,
        "random" : default_palette
    }

    def set_use_color(self, use_color):
        self.use_color = use_color

    def set_palette(self, name : str):
        self.current_palette = name

    def get_palette(self, name : str):
        palette_set = self.alt_palettes if self.alternation else self.palettes
        return palette_set.get(name, palette_set.get("default"))

    def get_position(self):
        return self.position

    def enter_position(self):
        self.position += 1
        return self.get_position()

    def leave_position(self):
        self.position -= 1

    def get_color(self):
        palette = self.get_palette(self.current_palette)
        return palette[self.color]

    def enter_color(self):
        if self.current_palette == "random":
            self.manage_random_palette()
        else:
            self.manage_color_alternation()
        self.color += 1
        return self.get_color()

    def leave_color(self):
        self.color -= 1

    def toggle_color_alternation(self):
        self.alternation = not self.alternation

    def manage_color_alternation(self):
        if self.get_position() == 0:
            self.toggle_color_alternation()

    def manage_random_palette(self):
        if self.get_position() == 0:
            random.shuffle(self.palettes["random"])
            self.alt_palettes["random"] = self.palettes["random"]

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
        if self.entered_count >= self.MAX_BARS:
            raise ValueError(f"The maximum number of bars {self.MAX_BARS} has been reached")
        position = self.enter_position()
        leave = self.enter_leave()
        color = self.enter_color()
        if self.use_color:
            bar = tqdm(total=total, desc=desc, position=position, leave=leave, colour=color)
        else:
            bar = tqdm(total=total, desc=desc, position=position, leave=leave)
        self.entered_bars[position] = bar
        self.entered_count += 1
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
            self.entered_count -= 1

            # now_current_position = get_position()
            # now_current_bar = entered_bars[now_current_position]
            # now_current_bar.update()

    def message(self, bar, message):
        position = self.find_bar_position(bar)
        bar.display(message, position+1)

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
    indexes = []
    bars = []

    def make_bar(self, bar_num, max):
        return Mtqdm().enter_bar(total=max, desc=f"Bar{bar_num}")

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
            Mtqdm().leave_bar(bar)

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

    def test_bars_3(self, times, total, delay):
        for n in range(times):
            with Mtqdm().open_bar(total=total) as bar:
                for o in range(total):
                    with Mtqdm().open_bar(total=total, desc="Some More") as bar2:
                        for p in range(total):
                            bar2.update()
                            time.sleep(delay)
                    bar.update()

    def test_bars_4(self, palette, times, count, total, delay):
        Mtqdm(palette=palette)
        for m in range(times):
            bars = [None for n in range(count)]
            for n in range(count):
                bars[n] = Mtqdm().enter_bar(total=total, desc=f"Bar{n}")
            for n in range(total):
                for bar in bars:
                    Mtqdm().update_bar(bar)
                time.sleep(delay)
            for n in range(count-1, -1, -1):
                Mtqdm().leave_bar(bars[n])

    def test_bars_5(self, min, max, delay):
        Mtqdm().use_color = False
        self.test_bars_2(min, max, delay)
        Mtqdm().use_color = True

    def test_bars_6(self, min, max, delay):
        Mtqdm().set_palette("random")
        self.test_bars_2(min, max, delay)

    def test_bars_7(self, min, max, delay):
        Mtqdm().set_palette("doesnotexist")
        self.test_bars_2(min, max, delay)

    def test_bars_8(self, delay):
        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "Please wait for this long operation")
            time.sleep(delay)
            Mtqdm().update_bar(bar)

    def run_test(self, test : int):
        {
            1 : lambda : self.test_bars_1(9, 3, 0.01),
            2 : lambda : self.test_bars_2(5, 15, 0.1),
            3 : lambda : self.test_bars_3(10, 10, .001),
            4 : lambda : self.test_bars_4("rainbow", 5, Mtqdm.MAX_BARS, 10, 1.0),
            5 : lambda : self.test_bars_5(5, 15, 0.1),
            6 : lambda : self.test_bars_6(5, 10, 0.1),
            7 : lambda : self.test_bars_7(5, 10, 0.1),
            8 : lambda : self.test_bars_8(3),
        }[test]()

if __name__ == '__main__':
    while True:
        MtqdmTester().run_test(int(input(f"Mtqdm Test (1..8)):")))
