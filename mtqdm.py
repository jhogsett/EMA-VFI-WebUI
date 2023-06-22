"""Multiple TQDM progress bar manager singleton class"""

import time
from tqdm import tqdm

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

    def enter_bar(self, total=100, description="Please Wait"):
        position = self.enter_position()
        leave = self.enter_leave()
        color = self.enter_color()
        bar = tqdm(total=total, desc=description, position=position, leave=leave, colour=color)
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

    def update_bar(self, bar, steps=1):
        bar.update(n=steps)

    def get_bar(self, index):
        return self.entered_bars[index]

    def get_bar_max(self, index):
        return self.bar_totals[index]




mtqdm = Mtqdm(palette="rainbow")

indexes = []
bars = []

def make_bar(bar_num, max):
    return mtqdm.enter_bar(total=max, description=f"Bar{bar_num}")

def test_bars(number_of_bars, number_of_steps, delay):
    global indexes, bars
    indexes = [0 for n in range(number_of_bars)]
    bars = [make_bar(n, number_of_steps ** n) for n in range(number_of_bars)]

    for n in range(1, 10000):
        keep_going = advance_indexes()
        if keep_going:
            time.sleep(delay)
            continue
        else:
            break

    for bar in reversed(bars):
        mtqdm.leave_bar(bar)

def advance_index(index):
    global indexes, bars
    value = indexes[index]
    max = mtqdm.get_bar_max(index)
    if index == 0 and value == max-1:
        bars[index].update()
        return False

    if value == max-1:
        indexes[index] = 0
        bars[index].reset()
        bars[index].refresh()
        return advance_index(index-1)
    else:
        indexes[index] = value + 1
        bars[index].update()
        return True

def advance_indexes():
    global indexes
    last_index = len(indexes)-1
    return advance_index(last_index)

test_bars(5, 2, 0.000000001)
