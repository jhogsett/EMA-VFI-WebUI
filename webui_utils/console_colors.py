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
    end = "m"
    close = "\x1b[0m"

    @staticmethod
    def ctext(text, color="red", style="bold"):
        color = ColorOut.colors[color]
        style = ColorOut.styles[style]
        return f"{ColorOut.start}{style};3{color}{ColorOut.end}{text.strip()}{ColorOut.close}"

    @staticmethod
    def cprint(text, color="red", style="bold"):
        print(ColorOut.ctext(text, color, style))
