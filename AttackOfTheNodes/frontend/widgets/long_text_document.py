"""A TextArea document which preserves each existing line separator exactly.

Textual's plain Document joins every line with the first separator it found.
Forms must keep mixed CRLF/CR/LF, Unicode separators, and trailing blank lines.
Edits still use Textual's locations, undo stack and normal caret behaviour.
"""
import re
from bisect import bisect_right
from textual.document._document import Document, EditResult


class LongTextDocument(Document):
    def __init__(self, text):
        self._load(text)

    def _load(self, text):
        parts = re.split(r'(\r\n|\r|\n)', text)
        self._lines = parts[::2]
        self._breaks = parts[1::2]
        self._newline = self._breaks[0] if self._breaks else '\n'
        self._offsets = [0]
        for line, ending in zip(self._lines, self._breaks):
            self._offsets.append(self._offsets[-1] + len(line) + len(ending))

    @property
    def text(self):
        return ''.join(line + ending for line, ending in zip(self._lines, self._breaks)) + self._lines[-1]

    def get_index_from_location(self, location):
        row, column = location
        if row >= self.line_count:
            return len(self.text)
        return self._offsets[row] + min(column, len(self._lines[row]))

    def get_location_from_index(self, index):
        if not 0 <= index <= len(self.text):
            raise ValueError(f'Index {index!r} is outside the document.')
        row = bisect_right(self._offsets, index) - 1
        return row, min(index - self._offsets[row], len(self._lines[row]))

    def get_text_range(self, start, end):
        start, end = sorted((start, end))
        return self.text[self.get_index_from_location(start):self.get_index_from_location(end)]

    def replace_range(self, start, end, text):
        start, end = sorted((start, end))
        before = self.text
        a, b = self.get_index_from_location(start), self.get_index_from_location(end)
        replaced = before[a:b]
        self._load(before[:a] + text + before[b:])
        return EditResult(self.get_location_from_index(a + len(text)), replaced)
