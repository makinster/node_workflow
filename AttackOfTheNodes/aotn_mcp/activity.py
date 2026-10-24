"""Bounded, read-only activity projections; never read requests or raw evidence."""
from contextlib import contextmanager
from datetime import datetime, timezone
import heapq
import json
import math
import os
from pathlib import Path
import re
import stat

RECORD_BYTES = 256 * 1024
SOURCE_BYTES = 8 * 1024 * 1024
DIRECTORY_ENTRIES = 2000
EVENT_LINE_BYTES = 64 * 1024
EVENT_LINES = 20000
FINDING_CHARS = 2000
TEXT_CHARS = 300
SOURCES = ('run_history', 'investigation_results', 'events.jsonl')
IDENTIFIER = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
REQUEST_ID = re.compile(r'i_\d{8}_\d{6}_[a-f0-9]{32}\Z')


def utc(value):
    if not isinstance(value, str) or len(value) > 64 or 'T' not in value:
        raise ValueError('expected an ISO 8601 timestamp with a time zone')
    moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('expected an ISO 8601 timestamp with a time zone')
    return moment.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('non-finite number')
        return result

    def invalid(_):
        raise ValueError('non-JSON number')

    result = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                        parse_float=number, parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError('expected a record')
    return result


@contextmanager
def directory(path):
    """Pin every directory component without following symlinks or creating it."""
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def regular(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('expected a regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            yield stream, info.st_size
    finally:
        os.close(fd)


def secrets_at(path):
    # Do not use a writer/repair helper or a loader that logs damaged contents.
    try:
        with directory(path) as parent, regular(parent, 'secrets.json') as (stream, size):
            if size > RECORD_BYTES:
                raise ValueError
            raw = stream.read(RECORD_BYTES + 1)
            if len(raw) != size:
                raise ValueError
            values = decode(raw)
            if any(not isinstance(value, str) for value in values.values()):
                raise ValueError
            for value in values.values():
                value.encode('utf-8')
            return sorted((value for value in values.values() if value), key=len, reverse=True)
    except FileNotFoundError:
        return []
    except (OSError, ValueError, RecursionError):
        raise ValueError('activity secrets could not be read safely') from None


class Reader:
    def __init__(self, since, limit, secrets):
        self.since, self.limit, self.secrets = since, limit, secrets
        self.skipped = dict.fromkeys(SOURCES, 0)
        self.truncated = set()
        self.heap = []
        self.sequence = 0

    def text(self, value, cap=TEXT_CHARS):
        from backend.hermes_investigations import redact
        if not isinstance(value, str):
            raise ValueError('expected text')
        value.encode('utf-8')
        for secret in self.secrets:
            value = value.replace(secret, '[redacted]')
        value = redact(value)
        return value if cap is None else value[:cap]

    def project(self, record, source):
        if source == 'run_history':
            if not isinstance(record.get('run_id'), str) or not IDENTIFIER.fullmatch(record['run_id']):
                raise ValueError('invalid run')
            stamp = utc(record.get('ended_at') or record.get('started_at'))
            item = dict(type='run', time=stamp, source=source,
                        run_id=self.text(record['run_id']),
                        workflow_name=self.text(record['workflow_name']),
                        final_state=self.text(record['final_state']))
            for key in ('workflow_id', 'started_at', 'ended_at'):
                if record.get(key) is not None:
                    item[key] = utc(record[key]) if key.endswith('_at') else self.text(record[key])
            for key in ('error_count', 'unhandled_error_count', 'output_count'):
                if key in record:
                    if type(record[key]) is not int or record[key] < 0:
                        raise ValueError('invalid count')
                    item[key] = record[key]
            return item
        if type(record.get('schema_version')) is not int or record['schema_version'] != 1:
            raise ValueError('unknown version')
        if source == 'investigation_results':
            rid, state = record.get('request_id'), record.get('state')
            if not isinstance(rid, str) or not REQUEST_ID.fullmatch(rid) or state not in ('ready', 'failed'):
                raise ValueError('invalid result')
            stamp = utc(record.get('finished_at'))
            finding = record.get('finding')
            if not isinstance(finding, str) or (state == 'ready' and not finding.strip()):
                raise ValueError('invalid finding')
            failure = None
            if state == 'failed':
                problem = record.get('failure')
                if not isinstance(problem, dict):
                    raise ValueError('invalid failure')
                failure = self.text(problem.get('code'))
            finding = self.text(finding, None) if state == 'ready' else ''
            return dict(type='investigation', time=stamp, source=source,
                        request_id=self.text(rid), state=state, finished_at=stamp,
                        finding=finding[:FINDING_CHARS],
                        finding_truncated=len(finding) > FINDING_CHARS,
                        failure=failure)
        kind = record.get('kind')
        if kind not in ('event', 'receipt'):
            raise ValueError('unknown event')
        item = dict(type='event', source=source, kind=kind,
                    time=utc(record.get('stage_at' if kind == 'receipt' else 'created_at')),
                    workflow=self.text(record['workflow']), stage=None,
                    summary=self.text(record.get('summary', '') if kind == 'receipt' else record['summary']))
        if kind == 'receipt':
            if record.get('stage') not in ('queued', 'skipped', 'handed_off', 'delivered', 'failed'):
                raise ValueError('unknown stage')
            item['stage'] = record['stage']
        else:
            item['name'] = self.text(record['name'])
        return item

    def add(self, raw, source, filename=None):
        try:
            record = decode(raw)
            if filename and record.get('request_id' if source == 'investigation_results' else 'run_id') != filename[:-5]:
                raise ValueError('mismatched record id')
            item = self.project(record, source)
            if self.since is not None and item['time'] < self.since:
                return
            self.sequence += 1
            heapq.heappush(self.heap, (item['time'], self.sequence, item))
            if len(self.heap) > self.limit:
                heapq.heappop(self.heap)
        except (ValueError, KeyError, TypeError, RecursionError, OverflowError):
            self.skipped[source] += 1

    def records(self, path, source):
        try:
            with directory(path) as parent:
                names = []
                with os.scandir(parent) as entries:
                    for index, entry in enumerate(entries):
                        if index >= DIRECTORY_ENTRIES:
                            self.truncated.add(source)
                            break
                        if entry.name.endswith('.json') and not entry.name.startswith('.'):
                            names.append(entry.name)
                consumed = 0
                for name in sorted(names, reverse=True):
                    try:
                        with regular(parent, name) as (stream, size):
                            if size > RECORD_BYTES:
                                self.skipped[source] += 1
                                continue
                            if consumed + size > SOURCE_BYTES:
                                self.truncated.add(source)
                                break
                            raw = stream.read(size + 1)
                            consumed += len(raw)
                            if len(raw) != size:
                                raise ValueError('record changed')
                            self.add(raw, source, name)
                    except (OSError, ValueError):
                        self.skipped[source] += 1
        except FileNotFoundError:
            pass
        except OSError:
            self.skipped[source] += 1

    def events(self, path):
        source = 'events.jsonl'
        try:
            with directory(path) as parent, regular(parent, source) as (stream, size):
                start = max(0, size - SOURCE_BYTES)
                self.truncated.update([source] if start else [])
                stream.seek(max(0, start - 1))
                fragment = bool(start and stream.read(1) != b'\n')
                stream.seek(start)
                data = stream.read(size - start)
                if len(data) != size - start:
                    raise ValueError('event log changed')
                left = 0
                if fragment:
                    # The byte-window's first partial record is not damage.
                    boundary = data.find(b'\n')
                    left = len(data) if boundary < 0 else boundary + 1
                end = len(data)
                if end > left and not data.endswith(b'\n'):
                    self.skipped[source] += 1  # An unfinished writer tail.
                    end = max(left, data.rfind(b'\n') + 1)
                count = 0
                while end > left and count < EVENT_LINES:
                    boundary = data.rfind(b'\n', left, end - 1)
                    begin = boundary + 1 if boundary >= left else left
                    if end - begin > EVENT_LINE_BYTES:
                        self.skipped[source] += 1
                    else:
                        self.add(data[begin:end], source)
                    end = begin
                    count += 1
                if end > left:
                    self.truncated.add(source)
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self.skipped[source] += 1


def get_activity(since=None, limit=10):
    from backend import persistence, hermes_folder
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be an integer from 1 to 100')
    try:
        since = utc(since) if since is not None else None
    except (ValueError, TypeError, OverflowError):
        raise ValueError('since must be an ISO 8601 timestamp with a time zone') from None
    reader = Reader(since, limit, secrets_at(persistence.SECRETS_DIR))
    reader.records(persistence.RUN_HISTORY_DIR, 'run_history')
    shared = hermes_folder.folder()
    reader.records(shared / 'investigations' / 'results', 'investigation_results')
    reader.events(shared)
    return dict(activity=[item for _, _, item in sorted(reader.heap, reverse=True)],
                skipped=sum(reader.skipped.values()), skipped_by_source=reader.skipped,
                truncated_sources=sorted(reader.truncated))
