"""Bounded UTF-8 file snapshots for Read lines and Find lines; no shell."""
from __future__ import annotations

import asyncio
from collections import deque
from contextlib import contextmanager
import os
from pathlib import Path
import stat

from .node_errors import NodeError
from .system_access import checked_path

MESSAGES = {
    'file_missing': 'This file was not found.',
    'not_regular': 'Choose a regular text file.',
    'file_unreadable': 'This file could not be read.',
    'not_utf8': 'This file is not UTF-8 text.',
    'file_too_large': 'This file is too large.',
    'line_too_long': 'A line in this file is too long.',
    'file_changed': 'This file changed while reading it.',
    'invalid_range': 'Check the line numbers.',
    'no_matches': 'No matching line to read.',
    'no_lines': 'This file has no lines.',
    'excerpt_too_long': 'The excerpt is too long.',
    'text_missing': 'Enter text to find.',
}


def failure(code):
    return NodeError(code, MESSAGES[code])


def integer(value, low, high, code='invalid_range'):
    if type(value) is not int or not low <= value <= high:
        raise failure(code)
    return value


def source(config, context):
    choice = config.get('input_source')
    if choice == 'Configured':
        return config.get('input')
    if choice == 'Upstream payload':
        return context.inputs.get('input')
    if choice == 'Vault':
        return context.memory_bank.read_persistent(config.get('input_vault_key', ''))
    raise NodeError('node_error', 'Choose an input source.')


def validate_outputs(config, extra=False):
    keys = []
    for enabled, key in [('vault_write', 'vault_write_key')] + (
            [('match_count_vault_write', 'match_count_vault_key')] if extra else []):
        if config.get(enabled):
            value = config.get(key)
            if not isinstance(value, str) or not value.strip() or value.strip() in keys:
                raise NodeError('node_error', 'Enter a different Vault key for each output.')
            keys.append(value.strip())


@contextmanager
def snapshot(raw, get_setting, max_mb):
    """Resolve through system_access, then open every component without links.

    O_NONBLOCK avoids hanging on a FIFO swapped into the final path. Directory
    descriptors pin the walk; a replacement symlink cannot redirect the open.
    """
    integer(max_mb, 1, 100, 'file_too_large')
    try:
        path = checked_path(raw, get_setting, what='file')
    except NodeError as exc:
        if exc.code == 'folder_missing':
            raise failure('file_missing') from None
        raise
    except (OSError, ValueError):
        raise failure('file_unreadable') from None
    if not all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise failure('file_unreadable')
    fd = None
    parent = None
    try:
        parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        initial = os.fstat(fd)
        if not stat.S_ISREG(initial.st_mode):
            raise failure('not_regular')
        if initial.st_size > max_mb * 1_000_000:
            raise failure('file_too_large')
        yield fd, initial.st_size
        final = os.fstat(fd)
        named = path.stat()
        if (final.st_size < initial.st_size or
                (named.st_dev, named.st_ino) != (initial.st_dev, initial.st_ino) or
                (final.st_size == initial.st_size and final.st_mtime_ns != initial.st_mtime_ns)):
            raise failure('file_changed')
    except NodeError:
        raise
    except FileNotFoundError:
        raise failure('file_changed' if fd is not None else 'file_missing') from None
    except (OSError, ValueError):
        raise failure('file_unreadable') from None
    finally:
        if fd is not None:
            os.close(fd)
        if parent is not None:
            os.close(parent)


async def lines(fd, size):
    """Stream the initial byte range; split LF only, strip a UTF-8 BOM once."""
    os.lseek(fd, 0, os.SEEK_SET)
    remaining, pending, first = size, b'', True
    while remaining:
        await asyncio.sleep(0)  # Stop cancels the task between bounded reads.
        chunk = os.read(fd, min(65536, remaining))
        if not chunk:
            raise failure('file_changed')
        remaining -= len(chunk)
        pieces = (pending + chunk).split(b'\n')
        pending = pieces.pop()
        for raw in pieces:
            if raw.endswith(b'\r'):
                raw = raw[:-1]
            text = decode(raw, first)
            first = False
            yield text + '\n'
        if len(pending) > 64000:
            raise failure('line_too_long')
    if pending:
        yield decode(pending, first)


def decode(raw, first):
    if len(raw) > 64000:
        raise failure('line_too_long')
    try:
        return raw.decode('utf-8-sig' if first else 'utf-8')
    except UnicodeError:
        raise failure('not_utf8') from None


async def find(config, context):
    needle = source(config, context)
    if not isinstance(needle, str) or not needle or '\n' in needle or '\r' in needle or len(needle) > 64000:
        raise failure('text_missing')
    cap = integer(config['max_matches'], 1, 1000)
    match_case = config.get('match_case', True)
    if not match_case:
        needle = needle.casefold()
    recent, count = deque(maxlen=cap), 0
    with snapshot(config.get('file'), context.get_setting, config['max_file_mb']) as (fd, size):
        number = 0
        async for line in lines(fd, size):
            number += 1
            haystack = line if match_case else line.casefold()
            if needle in haystack:
                count += 1
                recent.append(number)
    return list(recent), count


async def read(config, context):
    start = source(config, context)
    if isinstance(start, list):
        if not start:
            raise failure('no_matches')
        if len(start) > 1000 or any(type(n) is not int or n == 0 for n in start):
            raise failure('invalid_range')
        if config.get('use_match') not in ('First', 'Last'):
            raise failure('invalid_range')
        start = start[0 if config['use_match'] == 'First' else -1]
    if type(start) is not int or start == 0:
        raise failure('invalid_range')
    around = config.get('lines_around', False)
    end = config.get('to_line')
    if not around and (type(end) is not int or end == 0):
        raise failure('invalid_range')
    each = integer(config.get('each_side', 5), 0, 200) if around else 0
    max_text = integer(config['max_text'], 1, 20000, 'excerpt_too_long')
    with snapshot(config.get('file'), context.get_setting, config['max_file_mb']) as (fd, size):
        count = 0
        async for _ in lines(fd, size):
            count += 1
        if not count:
            if around:
                raise failure('no_lines')
            return ''
        def position(n):
            return n if n > 0 else max(1, count + n + 1)
        start = position(start)
        if start > count:
            raise failure('invalid_range')
        if around:
            start, end = max(1, start - each), min(count, start + each)
        else:
            end = min(count, position(end))
        if end < start:
            raise failure('invalid_range')
        if end - start + 1 > 500:
            raise failure('excerpt_too_long')
        excerpt, chars, byte_count, number = [], 0, 0, 0
        async for line in lines(fd, size):
            number += 1
            if start <= number <= end:
                chars += len(line)
                byte_count += len(line.encode('utf-8'))
                if chars > max_text or byte_count > 80000:
                    raise failure('excerpt_too_long')
                excerpt.append(line)
        return ''.join(excerpt)
