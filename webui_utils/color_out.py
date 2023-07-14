"""Simple class for outputing colored text in the console"""
class ColorOut:
    def __init__(self, text, color="red", style="bold"):
        ColorOut.cprint(text, color, style)

    colors = {
        "black" : "0",
        "red" : "1",
        "green" : "2",
        "yellow" : "3",
        "blue" : "4",
        "purple" : "5",
        "cyan" : "6",
        "white" : "7"
    }

    styles = {
        None : 0,
        "none" : "0",
        "bold"  : "1"
    }

    start = "\x1b["
    rgbstart = "\x1b[38;2;"
    end = "m"
    close = "\x1b[0m"

    @staticmethod
    def ctext(text, color="red", style="bold"):
        color = ColorOut.colors[color]
        style = ColorOut.styles[style]
        return f"{ColorOut.start}{style};3{color}{ColorOut.end}{text.strip()}{ColorOut.close}"

    @staticmethod
    def rgbtext(text, red, green, blue):
        color = f"{red};{green};{blue}"
        return f"{ColorOut.rgbstart}{color}{ColorOut.end}{text.strip()}{ColorOut.close}"

    @staticmethod
    def cprint(text, color="red", style="bold"):
        color = color.lower()
        try:
            list(ColorOut.colors.keys()).index(color)
            return print(ColorOut.ctext(text, color, style))
        except ValueError:
            pass

        # not a named color, might RGB
        parts = color.split(",")
        if len(parts) == 3:
            try:
                red = int(parts[0].strip())
                green = int(parts[1].strip())
                blue = int(parts[2].strip())
                return print(ColorOut.rgbtext(text, red, green, blue))
            except ValueError:
                pass

        # not RGB, might be Web color
        if color.startswith("#"):
            color = color[1:]
        try:
            red = int(color[0:2], base=16)
            green = int(color[2:4], base=16)
            blue = int(color[4:6], base=16)
            return print(ColorOut.rgbtext(text, red, green, blue))
        except ValueError:
            pass

        # color not understood
        return print(text)
