import time
import random
from mtqdm import Mtqdm # pylint: disable=import-error

class MtqdmTester():
    indexes = []
    bars = []

    def make_bar(self, bar_num, max):
        return Mtqdm().enter_bar(total=max, desc=f"Bar{bar_num}")

    def variable_bars(self, number_of_bars, number_of_steps, delay):
        _number_of_bars = random.randint(1, number_of_bars)
        MtqdmTester.indexes = [0 for n in range(_number_of_bars)]

        MtqdmTester.bars = []
        for n in range(_number_of_bars):
            _number_of_steps = random.randint(1, number_of_steps)
            MtqdmTester.bars.append(self.make_bar(n, _number_of_steps))

        for n in range(1, 100000):
            keep_going = self.advance_indexes()
            if keep_going:
                time.sleep(delay)
                continue
            else:
                break

        for bar in reversed(MtqdmTester.bars):
            Mtqdm().leave_bar(bar)

    def advance_index(self, index):
        global indexes, bars
        value = MtqdmTester.indexes[index]
        max = Mtqdm().get_bar_max(index)
        random_steps = 1 # random.randint(1, max)
        if index == 0 and value == max-1:
            Mtqdm().update_bar(MtqdmTester.bars[index], steps=random_steps)
            return False

        if value >= max-1:
            MtqdmTester.indexes[index] = 0
            MtqdmTester.bars[index].reset()
            MtqdmTester.bars[index].refresh()
            return self.advance_index(index-1)
        else:
            MtqdmTester.indexes[index] = value + 1
            Mtqdm().update_bar(MtqdmTester.bars[index], steps=random_steps)
            return True

    def advance_indexes(self):
        global indexes
        last_index = len(MtqdmTester.indexes)-1
        return self.advance_index(last_index)

    def optional_process(self, min, max, delay):
        count = random.randint(min, max)
        half = delay / 2.0
        delay = random.random() * half + half
        with Mtqdm().open_bar(desc="Optional Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                Mtqdm().update_bar(bar)

    def deep_process(self, min, max, delay):
        count = random.randint(min, max)
        half = delay / 2.0
        delay = random.random() * half + half
        with Mtqdm().open_bar(desc="Deep Process", total=count) as bar:
            for n in range(count):
                if count % min == 0:
                    self.optional_process(min, max, delay)
                time.sleep(delay)
                Mtqdm().update_bar(bar)

    def shallow_process(self, min, max, delay):
        count = random.randint(min, max)
        half = delay / 2.0
        delay = random.random() * half + half
        with Mtqdm().open_bar(desc="Shallow Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                self.deep_process(min, max, delay)
                Mtqdm().update_bar(bar)

    def main_process(self, min, max, delay):
        count = random.randint(min, max)
        half = delay / 2.0
        delay = random.random() * half + half
        with Mtqdm().open_bar(desc="Main Process", total=count) as bar:
            for n in range(count):
                time.sleep(delay)
                self.shallow_process(min, max, delay)
                Mtqdm().update_bar(bar)

    def optional_bar(self, min, max, delay):
        self.main_process(min, max, delay)

    def alternation_test(self, times, total, delay):
        for n in range(times):
            with Mtqdm().open_bar(total=total) as bar:
                for o in range(total):
                    with Mtqdm().open_bar(total=total, desc="Some More") as bar2:
                        for p in range(total):
                            Mtqdm().update_bar(bar2)
                            time.sleep(delay)
                    Mtqdm().update_bar(bar)

    def parallel_bars(self, times, count, total, delay):
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

    def no_color_bars(self, min, max, delay):
        Mtqdm().use_color = False
        self.variable_bars(min, max, delay)
        Mtqdm().use_color = True

    def bar_message(self, delay):
        with Mtqdm().open_bar(total=1, desc="FFmpeg") as bar:
            Mtqdm().message(bar, "This won't take but a moment")
            time.sleep(delay)
            with Mtqdm().open_bar(total=1, desc="More FFmpeg") as bar2:
                Mtqdm().message(bar2, "Forgot this was needed too")
                time.sleep(delay)
                Mtqdm().update_bar(bar2)
            Mtqdm().update_bar(bar)

    def auto_total_bar(self, delay):
        with Mtqdm().open_bar(total=10, desc="Process stop short", auto_total=True) as bar:
            Mtqdm().update_bar(bar)
            time.sleep(delay)
            Mtqdm().update_bar(bar)
            time.sleep(delay)
            Mtqdm().update_bar(bar)
            time.sleep(delay)

    def bar_additional_leave(self, times, total, delay):
        for n in range(times):
            with Mtqdm().open_bar(total=total) as bar:
                for o in range(total):
                    with Mtqdm().open_bar(total=total, desc="Some More", leave=True) as bar2:
                        for p in range(total):
                            Mtqdm().update_bar(bar2)
                            time.sleep(delay)
                    Mtqdm().update_bar(bar)

    def negative_updates(self, times, total, delay):
        for n in range(times):
            with Mtqdm().open_bar(total=total, desc="Snoozing") as bar:
                for m in range(total):
                    Mtqdm().update_bar(bar, steps=1)
                    time.sleep(delay)
                for m in range(total-1, -1, -1):
                    Mtqdm().update_bar(bar, steps=-1)
                    time.sleep(delay)

    def insanity_bars(self, times, count, total, delay):
        for m in range(times):
            bars = [None for n in range(count)]
            for n in range(count):
                bars[n] = Mtqdm().enter_bar(total=total, desc=f"Bar{n}")
            for n in range(total):
                for bar in bars:
                    _range = int(total / 10)
                    steps = random.randint(-_range, +_range)
                    Mtqdm().update_bar(bar, steps=steps)
                time.sleep(delay)
            for n in range(count-1, -1, -1):
                Mtqdm().leave_bar(bars[n])

    def absurdity_bars(self, times, count, total, delay):
        bars = [None for n in range(count)]
        curr = [0 for n in range(count)]
        dirs = [1 for n in range(count)]
        for n in range(count):
            bars[n] = Mtqdm().enter_bar(total=total, desc=f"Bar{n}")
        for m in range(times):
            for n in range(count):
                incr = (n + 1) * dirs[n]
                next_val = curr[n] + incr
                if next_val >= total or next_val < 0:
                    dirs[n] *= -1
                else:
                    curr[n] += incr
                    Mtqdm().update_bar(bars[n], steps=incr)
                    time.sleep(delay)
        for n in range(count-1, -1, -1):
            Mtqdm().leave_bar(bars[n])

    def test_palettes(self):
        return [
            {
                "Default" : "default"
            },
            {
                "Rainbow" : "rainbow"
            },
            {
                "Random" : "random"
            },
            {
                "BeMine" : "bemine"
            },
            {
                "Random BeMine" : "randbemine"
            },
            {
                "Non-existent" : "doesnotexist"
            },
        ]

    def tests(self):
        return [
            {
                "Processes, Sub-Processes & Optional Process" : lambda : self.optional_bar(5, 10, 0.001)
            },
            {
                "Color Alternation Test" : lambda : self.alternation_test(5, 5, .001)
            },
            {
                "Simulataneous Parallel Bars" : lambda : self.parallel_bars(1, Mtqdm.MAX_BARS, 10, 1.0)
            },
            {
                "Disabled Colors" : lambda : self.no_color_bars(3, 10, 0.1)
            },
            {
                "Random Bars" : lambda : self.variable_bars(9, 10, 0.00001)
            },
            {
                "Bar Message Test" : lambda : self.bar_message(3)
            },
            {
                "Auto-Total On Close" : lambda : self.auto_total_bar(1.5)
            },
            {
                "Additional Leaves" : lambda : self.bar_additional_leave(10, 10, .001)
            },
            {
                "Negative Updates" : lambda : self.negative_updates(6, 100, .01)
            },
            {
                "Insanity Bars" : lambda : self.insanity_bars(20, Mtqdm.MAX_BARS, 25, 0.025)
            },
            {
                "Absurdity Bars" : lambda : self.absurdity_bars(1000, Mtqdm.MAX_BARS, 50, 0.00000001)
            },
        ]

    def run_test(self, palette : int, test : int):
        palette_name = list(MtqdmTester().test_palettes()[palette].values())[0]
        Mtqdm().set_palette(palette_name)
        list(MtqdmTester().tests()[test].values())[0]()

if __name__ == '__main__':
    while True:
        tests = MtqdmTester().tests()
        palettes = MtqdmTester().test_palettes()

        default_test = random.randint(1, len(tests))
        default_palette = random.randint(1, len(palettes))

        while True:
            print()
            for index, test in enumerate(tests):
                print(f"{index + 1} : {list(test.keys())[0]}")
            test_input = input(
                f"Test to run [1 .. {len(tests)}] ({default_test}) :") or default_test
            test = int(test_input) - 1
            if 0 <= test < len(tests):
                break

        while True:
            print()
            for index, palette in enumerate(palettes):
                print(f"{index + 1} : {list(palette.keys())[0]}")
            palette_input = input(
                f"Palette to use [1 .. {len(palettes)}] ({default_palette}) :") or default_palette
            palette = int(palette_input) - 1
            if 0 <= palette < len(palettes):
                break

        print()
        print("CTRL-C to halt")
        print()

        try:
            MtqdmTester().run_test(palette, test)
        except KeyboardInterrupt:
            Mtqdm().reset()
