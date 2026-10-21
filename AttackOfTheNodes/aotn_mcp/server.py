"""Dependency-free MCP 2025-11-25 stdio server (newline-delimited JSON-RPC)."""
import argparse
import asyncio
import json
import logging
import math
import os
from pathlib import Path
import signal
import sys

from .processes import kill_and_reap, subreaper
from .tools import BY_NAME, TOOLS, validate_arguments

REQUEST_LIMIT = 1024 * 1024
RESPONSE_LIMIT = 16 * 1024 * 1024
VERSIONS = ('2025-11-25', '2025-06-18', '2024-11-05')
APP = Path(__file__).resolve().parent.parent


class RPCError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def decode(raw):
    def invalid(value):
        raise ValueError(f'non-JSON number: {value}')
    return json.loads(raw, parse_constant=invalid)


def tool_result(payload, version):
    if 'error' in payload:
        return {'content': [{'type': 'text', 'text': payload['error']}], 'isError': True}
    result = payload['result']
    response = {'content': [{'type': 'text', 'text': json.dumps(result, allow_nan=False)}],
                'isError': bool(payload.get('run') and result['exit_code'])}
    if version != '2024-11-05':
        response['structuredContent'] = result
    return response


class Server:
    def __init__(self, data, timeout):
        self.data, self.timeout = data, timeout
        self.version = None
        self.ready = False
        self.tasks = {}
        self.lock = asyncio.Lock()
        self.linux = subreaper()
        self.cleanup_failed = False

    def send(self, request_id, result=None, error=None):
        message = {'jsonrpc': '2.0', 'id': request_id}
        message['error' if error else 'result'] = error if error else result
        sys.stdout.write(json.dumps(message, ensure_ascii=True, allow_nan=False) + '\n')
        sys.stdout.flush()

    async def worker(self, name, arguments):
        async with self.lock:
            if self.cleanup_failed:
                return {'error': 'previous descendant cleanup failed; no further tools will start'}
            env = {**os.environ, 'AOTN_DATA_DIR': str(self.data)}
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'aotn_mcp.worker', cwd=APP, env=env,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=None, start_new_session=True)
            try:
                proc.stdin.write(json.dumps({'name': name, 'arguments': arguments}).encode())
                await proc.stdin.drain()
                proc.stdin.close()
                chunks, size = [], 0
                while chunk := await proc.stdout.read(65536):
                    size += len(chunk)
                    if size > RESPONSE_LIMIT:
                        return {'error': 'tool response exceeds 16 MiB'}
                    chunks.append(chunk)
                code = await proc.wait()
                if code:
                    return {'error': f'tool worker failed (exit {code}); see server stderr'}
                return decode(b''.join(chunks))
            finally:
                try:
                    kill_and_reap(proc.pid, self.linux)
                    await asyncio.wait_for(proc.wait(), 1)
                except (OSError, TimeoutError) as exc:
                    self.cleanup_failed = True
                    raise RuntimeError(f'worker cleanup failed: {exc}') from exc

    async def call(self, request_id, name, arguments):
        try:
            try:
                async with asyncio.timeout(self.timeout):
                    payload = await self.worker(name, arguments)
            except TimeoutError:
                payload = {'error': f'tool call timed out after {self.timeout:g} seconds; worker terminated'}
            self.send(request_id, tool_result(payload, self.version))
        except asyncio.CancelledError:
            # Cancellation has no response; the worker's finally owns cleanup.
            pass
        except Exception as exc:
            logging.exception('MCP tool call failed')
            self.send(request_id, tool_result({'error': str(exc)}, self.version))

    def accept(self, message):
        request_id = None
        try:
            if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
                raise RPCError(-32600, 'invalid JSON-RPC request')
            request_id = message.get('id')
            if 'id' in message and (type(request_id) not in (str, int)):
                request_id = None
                raise RPCError(-32600, 'request id must be a string or integer')
            method = message.get('method')
            if not isinstance(method, str):
                raise RPCError(-32600, 'method must be a string')
            params = message.get('params', {})
            if not isinstance(params, dict):
                raise RPCError(-32602, 'params must be an object')
            if 'id' not in message:
                if method == 'notifications/initialized' and self.version:
                    self.ready = True
                elif method == 'notifications/cancelled':
                    cancel_id = params.get('requestId')
                    task = self.tasks.get(cancel_id) if type(cancel_id) in (str, int) else None
                    if task:
                        task.cancel()
                return  # Notifications never receive responses.
            if request_id in self.tasks:
                raise RPCError(-32600, 'duplicate in-flight request id')
            if method == 'initialize':
                if self.version:
                    raise RPCError(-32600, 'already initialized')
                if not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                    raise RPCError(-32602, 'initialize requires protocolVersion, capabilities and clientInfo')
                self.version = params['protocolVersion'] if params['protocolVersion'] in VERSIONS else VERSIONS[0]
                self.send(request_id, {'protocolVersion': self.version,
                                      'capabilities': {'tools': {'listChanged': False}},
                                      'serverInfo': {'name': 'aotn', 'version': '0.1.0'}})
            elif method == 'ping':
                self.send(request_id, {})
            elif not self.ready:
                raise RPCError(-32000, 'initialize and send notifications/initialized first')
            elif method == 'tools/list':
                if params.get('cursor'):
                    raise RPCError(-32602, 'this tool list has no pagination cursor')
                tools = TOOLS if self.version != '2024-11-05' else [
                    {k: v for k, v in tool.items() if k != 'outputSchema'} for tool in TOOLS]
                self.send(request_id, {'tools': tools})
            elif method == 'tools/call':
                name, arguments = params.get('name'), params.get('arguments', {})
                if not isinstance(name, str) or name not in BY_NAME:
                    raise RPCError(-32602, 'unknown tool')
                try:
                    validate_arguments(name, arguments)
                except ValueError as exc:
                    self.send(request_id, tool_result({'error': str(exc)}, self.version))
                    return
                if len(self.tasks) >= 16:
                    raise RPCError(-32000, 'too many pending tool calls')
                task = asyncio.create_task(self.call(request_id, name, arguments))
                self.tasks[request_id] = task
                task.add_done_callback(lambda done, key=request_id: self.tasks.pop(key, None))
            else:
                raise RPCError(-32601, 'method not found')
        except RPCError as exc:
            if not isinstance(message, dict) or 'id' in message or exc.code == -32600:
                self.send(request_id, error={'code': exc.code, 'message': str(exc)})

    async def serve(self):
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(limit=REQUEST_LIMIT)
        transport, _ = await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
        current = asyncio.current_task()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, current.cancel)
        try:
            while True:
                try:
                    line = await reader.readline()
                    if not line:
                        break
                    message = decode(line)
                except (ValueError, UnicodeError, RecursionError) as exc:
                    self.send(None, error={'code': -32700, 'message': 'invalid or oversized JSON message'})
                    if isinstance(exc, ValueError) and 'limit' in str(exc).lower():
                        break
                    continue
                self.accept(message)
        finally:
            transport.close()
            tasks = list(self.tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='aotn mcp', description=__doc__)
    parser.add_argument('--data-dir', help='AOTN data root; overrides AOTN_DATA_DIR')
    parser.add_argument('--call-timeout', type=float, default=60, help='per-call deadline in seconds, including queue time (default 60)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.call_timeout) or args.call_timeout <= 0:
        parser.error('--call-timeout must be a positive finite number')
    # Match persistence.resolve_data_dir(), including whitespace handling.
    raw_data = str(args.data_dir or os.environ.get('AOTN_DATA_DIR', '') or APP).strip()
    data = Path(raw_data or APP).expanduser().resolve()
    for target in (data, (data / 'workflows').resolve()):
        for parent in (target, *target.parents):
            if (parent.name == 'workflows' and parent.parent.name == 'AttackOfTheNodes'
                    and (parent.parent.parent / '.git').exists()):
                parser.error('MCP data directory must not select a repository workflows folder; use --data-dir')
    os.environ['AOTN_DATA_DIR'] = str(data)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    try:
        asyncio.run(Server(data, args.call_timeout).serve())
    except asyncio.CancelledError:
        pass
    except (OSError, RuntimeError) as exc:
        print(f'aotn mcp: {exc}', file=sys.stderr)
        return 70
    return 0
