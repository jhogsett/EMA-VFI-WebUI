"""Multiple TQDM progress bar manager singleton class"""
import random
from contextlib import contextmanager
from tqdm import tqdm

class Mtqdm():
    """Manage multiple nested tqdm progress bars with optional auto-coloring"""
    def __new__(cls, use_color : bool=True, palette : str="default"):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Mtqdm, cls).__new__(cls)
            cls.instance.init(use_color, palette)
        return cls.instance

    MAX_BARS = 9
    MAX_COLORS = MAX_BARS

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

    subdued_colors = {
        "red" : "#ffb3b3",
        "orange" : "#ffddb3",
        "yellow" : "#ffffb3",
        "green" : "#b3ffb3",
        "blue" : "#b3b3ff",
        "purple" : "#ddb3ff",
        "cyan" : "#b3ffff",
        "magenta" : "#ffb3ff",
        "white" : "#d9d9d9"}

    alt_subdued_colors = {
        "red" : "#ffcccc",
        "orange" : "#ffe8cc",
        "yellow" : "#ffffcc",
        "green" : "#ccffcc",
        "blue" : "#ccccff",
        "purple" : "#e8ccff",
        "cyan" : "#ccffff",
        "magenta" : "#ffccff",
        "white" : "#e6e6e6"}

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

    bemine_palette = [
        subdued_colors["green"],
        subdued_colors["yellow"],
        subdued_colors["orange"],
        subdued_colors["red"],
        subdued_colors["blue"],
        subdued_colors["purple"],
        subdued_colors["magenta"],
        subdued_colors["cyan"],
        subdued_colors["white"]]

    bemine_palette_alt = [
        alt_subdued_colors["green"],
        alt_subdued_colors["yellow"],
        alt_subdued_colors["orange"],
        alt_subdued_colors["red"],
        alt_subdued_colors["blue"],
        alt_subdued_colors["purple"],
        alt_subdued_colors["magenta"],
        alt_subdued_colors["cyan"],
        alt_subdued_colors["white"]]

    palettes = {
        "default" : default_palette,
        "rainbow" : rainbow_palette,
        "bemine" : bemine_palette,
        "random" : default_palette.copy(),
        "randbemine" : bemine_palette.copy()
    }

    alt_palettes = {
        "default" : default_palette_alt,
        "rainbow" : rainbow_palette_alt,
        "bemine" : bemine_palette_alt,
        "random" : default_palette.copy(),
        "randbemine" : bemine_palette_alt.copy()
    }

    def init(self, use_color : bool=True, palette : str="default"):
        """Initialize the singleton class"""
        self.use_color = use_color
        self.current_palette = palette

        # tracks currently open bars
        self.entered_bars = [None for n in range(Mtqdm.MAX_BARS)]
        self.entered_count = 0

        # tracks totals for current open bars
        self.bar_totals = [0 for n in range(Mtqdm.MAX_BARS)]

        # seta up for first open bar
        self.position = -1
        self.color = -1
        self.leave = -1

        # alternates are dimmer, use brighter ones at first (less surprising)
        self.alternation = True

        # tracks whether messages were sent, to clear them on bar closing
        self.bar_message = [-1 for n in range(Mtqdm.MAX_BARS)]

        # tracks auto-totalling for bars
        self.bar_auto_total = [False for n in range(Mtqdm.MAX_BARS)]
        self.bar_updates = [0 for n in range(Mtqdm.MAX_BARS)]

    def reset(self):
        for index in range(Mtqdm.MAX_BARS - 1, -1, -1):
            if self.entered_bars[index]:
                self.leave_bar(self.entered_bars[index])
        self.init()

    @contextmanager
    def open_bar(self, total=100, desc="Calming...", leave=False, auto_total=False):
        try:
            bar = self.enter_bar(total=total, desc=desc, leave=leave, auto_total=auto_total)
            yield bar
        finally:
            self.leave_bar(bar)

    def enter_bar(self, total=100, desc="Calming...", leave=False, auto_total=False):
        """Open a new bar"""
        if self.entered_count >= self.MAX_BARS:
            raise ValueError(f"The maximum number of bars {self.MAX_BARS} has been reached")
        position = self._enter_position()
        leave = self._enter_leave(leave)
        color = self._enter_color()

        if self.use_color:
            bar = tqdm(total=total, desc=desc, position=position, leave=leave, colour=color)
        else:
            bar = tqdm(total=total, desc=desc, position=position, leave=leave)

        self.entered_bars[position] = bar
        self.entered_count += 1
        self.bar_totals[position] = total
        self.bar_message[position] = -1
        self.bar_auto_total[position] = auto_total
        self.bar_updates[position] = 0
        return bar

    def leave_bar(self, bar):
        """Close a previously opened bar"""
        position = self._find_bar_position(bar)
        if position != None:
            self._leave_color()
            self._leave_leave()
            self._leave_position()

            # if a message was displayed, clear it
            bar_message_pos = self.bar_message[position]
            if bar_message_pos >= 0:
                bar.display("", bar_message_pos)
                self.bar_message[position] = -1

            # if auto totalling
            if self.bar_auto_total[position]:
                remainder = self.bar_totals[position] - self.bar_updates[position]
                self.update_bar(bar, steps=remainder)

            bar.close()
            self.entered_bars[position] = None
            self.entered_count -= 1
            self.bar_totals[position] = 0
            self.bar_message[position] = -1
            self.bar_auto_total[position] = False
            self.bar_updates[position] = 0

    def set_use_color(self, use_color):
        """True to use colorful bars, False to use default bars,
        set at the singleton level for newly opened bars"""
        self.use_color = use_color

    def set_palette(self, name : str):
        """Set the name of the current color palette to use"""
        self.current_palette = name

    def get_palette(self) -> str:
        """Get the name of the current color palette in use"""
        return self.current_palette

    def message(self, bar, message=""):
        position = self._find_bar_position(bar)
        self.bar_message[position] = position + 1
        if self.use_color:
            palette = self._get_palette(self.current_palette)
            color = palette[position]
            message = self._webcolor_text(message, color)
        bar.display(message, position + 1)

    def update_bar(self, bar, steps=1):
        """Update a bar's progress"""
        position = self._find_bar_position(bar)
        current_progress = self.bar_updates[position]
        new_progress = current_progress + steps
        progress_diff = new_progress - current_progress

        # don't let positive updates go above total
        total = self.bar_totals[position]
        if new_progress > total:
            steps = total - current_progress

        # don't let negative updates go below zero
        if new_progress < 0:
            steps = -current_progress

        new_progress = current_progress + steps
        self.bar_updates[position] += steps
        bar.update(n=steps)

        # negative and 100% updates don't refresh automatically
        if progress_diff <= 0 or new_progress == total:
        # if progress_diff < 0:
            bar.refresh()

    def get_bar(self, index):
        return self.entered_bars[index]

    def get_bar_max(self, index):
        """Get the total for a bar by index"""
        return self.bar_totals[index]

    def _get_palette(self, name : str):
        palette_set = self.alt_palettes if self.alternation else self.palettes
        return palette_set.get(name, palette_set.get("default"))

    def _get_position(self):
        return self.position

    def _enter_position(self):
        self.position += 1
        return self._get_position()

    def _leave_position(self):
        self.position -= 1

    def _get_color(self):
        palette = self._get_palette(self.current_palette)
        return palette[self.color]

    def _enter_color(self):
        if self.current_palette in ["random", "randbemine"]:
            self._manage_random_palette()
        else:
            self._manage_color_alternation()
        self.color += 1
        return self._get_color()

    def _leave_color(self):
        self.color -= 1

    def _toggle_color_alternation(self):
        self.alternation = not self.alternation

    def _manage_color_alternation(self):
        if self._get_position() == 0:
            self._toggle_color_alternation()

    def _manage_random_palette(self):
        if self._get_position() == 0:
            random.shuffle(self.palettes[self.current_palette])
            self.alt_palettes[self.current_palette] = self.palettes[self.current_palette]

    def _get_leave(self, override):
        return override or self.leave == 0

    def _enter_leave(self, override):
        self.leave += 1
        return self._get_leave(override)

    def _leave_leave(self):
        self.leave -= 1

    # bar display position is managed to be the same as the index into bar lists
    def _find_bar_position(self, bar):
        try:
            return self.entered_bars.index(bar)
        except ValueError:
            return None

    RGBSTART = "\x1b[38;2;"
    RGBEND = "m"
    RGBCLOSE = "\x1b[0m"

    def _webcolor_text(self, text : str, color : str) -> str:
        assert color.startswith("#") and len(color) == 7
        red = int(color[1:3], base=16)
        green = int(color[3:5], base=16)
        blue = int(color[5:7], base=16)
        color = f"{red};{green};{blue}"
        return f"{self.RGBSTART}{color}{self.RGBEND}{text.strip()}{self.RGBCLOSE}"
