class Jot():
    """Simple class for creating quick multi-line reports"""
    def __init__(self, title=None, file=None):
        self.lines = []
        self.title = title
        self.file = file

    def __enter__(self):
        return self

    def __exit__(self, _1, _2, _3):
        self.keep()

    def __str__(self):
        return self.grab()

    def __repr__(self):
        return self.grab()

    BLANK = ""

    def down(self, text=BLANK):
        """Jot down something in the report, turns argument into a string"""
        self.lines.append(str(text))
    add = down

    def grab(self, separator_line = BLANK):
        """Grab a current version of the report"""
        _report = []
        if self.title:
            _report.append(f"{self.title}")
            if separator_line:
                _report.append(separator_line)
        _report += self.lines
        return "\r\n".join(_report)
    report = grab

    def keep(self):
        """Keep the report on disk if there's a filename, returns the lines list"""
        if self.file:
            with open(self.file, "w", encoding="UTF-8") as file:
                file.write(self.grab())
        return self.lines
    save = keep

    def wipe(self):
        """Wipe out the current report, returns the former lines list"""
        lines_before = self.lines
        self.lines = []
        return lines_before
    clear = wipe
