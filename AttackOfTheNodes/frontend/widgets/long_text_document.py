"""LF edit coordinates with a separate, lossless record of line separators.

Native history stores ranges in rows/columns. Re-parsing a raw CR followed by
an inserted LF would coalesce two logical breaks and make those ranges invalid.
Keep the lines and their separators separately, including inside undo records.
"""
import re
from textual.document._document import Document, EditResult


def split_lines(text):
    parts = re.split(r'(\r\n|\r|\n)', text)
    return parts[::2], parts[1::2]


def logical_text(text):
    return '\n'.join(split_lines(text)[0])


def line_ending_style(text):
    endings = set(split_lines(text)[1])
    return 'mixed' if len(endings) > 1 else next(iter(endings), '\n')


class LongTextDocument(Document):
    def __init__(self, text):
        self._lines, self._breaks = split_lines(text)
        self._newline = '\n'

    @property
    def saved_text(self):
        return self._join(self._lines, self._breaks, prevent_coalescence=True)

    @staticmethod
    def _join(lines, breaks, *, prevent_coalescence=False):
        parts = []
        for index, ending in enumerate(breaks):
            # A newly adjacent CR and LF must still represent two source lines
            # after reopening. Keep the CR and encode the next break as CRLF.
            if (prevent_coalescence and index and not lines[index]
                    and breaks[index - 1] == '\r' and ending == '\n'):
                ending = '\r\n'
            parts.extend((lines[index], ending))
        return ''.join(parts) + lines[-1]

    def _raw_range(self, start, end):
        top_row, top_column = start
        bottom_row, bottom_column = end
        if top_row == bottom_row:
            return self._lines[top_row][top_column:bottom_column]
        lines = self._lines[top_row:bottom_row + 1].copy()
        lines[0] = lines[0][top_column:]
        lines[-1] = lines[-1][:bottom_column]
        return self._join(lines, self._breaks[top_row:bottom_row], prevent_coalescence=True)

    def replace_range(self, start, end, text):
        start, end = sorted((start, end))
        # Textual can delete through a location one row beyond the document.
        start = self.get_location_from_index(min(self.get_index_from_location(start), len(self.text)))
        end = self.get_location_from_index(min(self.get_index_from_location(end), len(self.text)))
        top_row, top_column = start
        bottom_row, bottom_column = end
        replaced = self._raw_range(start, end)
        inserted_lines, inserted_breaks = split_lines(text)
        end_column = len(inserted_lines[-1]) + (top_column if len(inserted_lines) == 1 else 0)
        inserted_lines[0] = self._lines[top_row][:top_column] + inserted_lines[0]
        inserted_lines[-1] += self._lines[bottom_row][bottom_column:]
        self._lines[top_row:bottom_row + 1] = inserted_lines
        self._breaks[top_row:bottom_row] = inserted_breaks
        return EditResult((top_row + len(inserted_lines) - 1, end_column), replaced)
