class Jot():
    """Simple class to ease creating text multi-line reports"""
    def __init__(self, title=None, file=None):
        self.lines = []
        self.title = title
        self.file = file

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.write()

    def __str__(self):
        return self.report()

    BLANK = ""

    def add(self, text=BLANK):
        self.lines.append(str(text))
    down = add

    def report(self):
        _report = []
        if self.title:
            _report.append(f"[{self.title}]")
            _report.append(self.BLANK)
        _report += self.lines
        return "\r\n".join(_report)
    grab = report

    def write(self):
        if self.file:
            with open(self.file, "w", encoding="UTF-8") as file:
                file.write(self.report())
    save = write
