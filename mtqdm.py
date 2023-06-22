import time
from tqdm import tqdm

red = "#FF0000"
orange = "#FF7F00"
yellow = "#FFFF00"
green = "#00FF00"
blue = "#0000FF"
purple = "#7F00FF"
cyan = "#00FFFF"
magenta = "#FF00FF"
white = "#FFFFFF"
default_palette = [green, yellow, orange, red, blue, purple, magenta, cyan, white]
rainbow_palette = [red, orange, yellow, green, blue, purple, magenta, cyan, white]
max_bars = 9
current_palette = default_palette
entered_bars = [None for n in range(max_bars)]
bar_totals = [0 for n in range(max_bars)]

position = -1
def get_position():
   global position
   return position

def enter_position():
    global position
    position += 1
    return get_position()

def leave_position():
    global position
    position -= 1

color = -1
def get_color():
    global current_palette, color
    return current_palette[color]

def enter_color():
    global color
    color += 1
    return get_color()

def leave_color():
    global color
    color -= 1

leave = -1
def get_leave():
    global leave
    return leave == 0

def enter_leave():
    global leave
    leave += 1
    return get_leave()

def leave_leave():
    global leave
    leave -= 1

def find_bar_position(bar):
    try:
        return entered_bars.index(bar)
    except ValueError:
        return None

def enter_bar(total=100, description="wait"):
    position = enter_position()
    leave = enter_leave()
    color = enter_color()
    bar = tqdm(total=total, desc=description, position=position, leave=leave, colour=color)
    entered_bars[position] = bar
    bar_totals[position] = total
    return bar

def leave_bar(bar):
    global current_position, entered_bars

    position = find_bar_position(bar)
    if position != None:

        # current_position = get_position()
        # if position < current_position:
        #     deeper_bar = entered_bars(position+1)
        #     leave_bar(deeper_bar)
        #     return

        leave_color()
        leave_leave()
        leave_position()
        bar.close()
        entered_bars[position] = None

        # now_current_position = get_position()
        # now_current_bar = entered_bars[now_current_position]
        # now_current_bar.update()

def update_bar(bar, steps=1):
    bar.update(n=steps)

def get_bar(index):
    return entered_bars[index]

def get_bar_max(index):
    return bar_totals[index]

indexes = []
bars = []

def advance_index(index):
    global indexes, bars
    value = indexes[index]
    max = get_bar_max(index)
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

def make_bar(bar_num, max):
    return enter_bar(total=max, description=f"Bar{bar_num}")

#############

def test_bars(number_of_bars, number_of_steps, delay):
    global indexes, bars
    indexes = [0 for n in range(number_of_bars)]
    bars = [make_bar(n, number_of_steps) for n in range(number_of_bars)]

    for n in range(1, 10000):
        keep_going = advance_indexes()
        if keep_going:
            time.sleep(delay)
            continue
        else:
            break

    for bar in reversed(bars):
        leave_bar(bar)

    assert(n == number_of_steps ** number_of_bars)

# cache bars for reuse with a unique name
# - so they can be reentered repeatedly by a separate process run

# request to enter a bar with a unique name
# - does so if not in use, otherwise error
# maybe specify parent bar

# in the case of auto-fill there are three vars:
# 0: auto-fill
# 1: frame restore
# 2: frame search

# frame search could run on it's own, or as part of frame restore, or auto-fill via frame restore
# it won't know it's parent
# parents will know children bars



test_bars(9, 2, 0.000000001)

# bar1 = enter_bar()
# bar2 = enter_bar()
# bar3 = enter_bar()
# for n in range (100):
#     bar3.update()
#     time.sleep(0.1)