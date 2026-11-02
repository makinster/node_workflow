"""HTTP Request scheme boundary, using real urllib dispatch with fake transports."""
from email.message import Message
from io import BytesIO
import socket
import urllib.request
import urllib.response

import pytest

from tests.test_meta_nodes import runner


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Scheme tests must not read local URLs or use live transports')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(urllib.request.FileHandler, 'file_open', forbidden)
    monkeypatch.setattr(urllib.request.DataHandler, 'data_open', forbidden)
    monkeypatch.setattr(urllib.request.FTPHandler, 'ftp_open', forbidden)
    monkeypatch.setattr(urllib.request, '_opener', None)


@pytest.mark.asyncio
@pytest.mark.parametrize('url', [
    'file:///tmp/example.txt', 'FILE:///tmp/example.txt', 'data:text/plain,hello',
    'ftp://example.invalid/a', 'javascript:alert(1)', 'mailto:user@example.invalid',
    '/tmp/example.txt', '//example.invalid/a', 'example.invalid/a',
])
@pytest.mark.parametrize('mode', ['text', 'file'])
async def test_initial_non_http_scheme_fails_before_any_request(url, mode, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('An invalid URL must not open any request')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr('backend.nodes.io.http_request_node.build_opener', forbidden)
    node, ctx, _, done, errors = runner('http_request_node', dict(url=url, response_mode=mode))
    await node.execute(ctx)
    assert not done and len(errors) == 1
    assert errors[0].code == 'unsupported_url_scheme'
    assert str(errors[0]) == 'Only http:// and https:// URLs are supported.'


def redirect_transport(monkeypatch, destination, code):
    calls, responses = [], []
    def open_response(_handler, request):
        calls.append(request.full_url)
        headers = Message()
        status = code if len(calls) == 1 else 200
        if len(calls) == 1:
            headers['Location'] = destination
        headers['Content-Type'] = 'text/plain'
        result = urllib.response.addinfourl(BytesIO(b'hello'), headers, request.full_url, status)
        result.msg = 'Redirect' if status != 200 else 'OK'
        responses.append(result)
        return result
    monkeypatch.setattr(urllib.request.HTTPHandler, 'http_open', open_response)
    monkeypatch.setattr(urllib.request.HTTPSHandler, 'https_open', open_response)
    return calls, responses


@pytest.mark.asyncio
@pytest.mark.parametrize('code', [301, 302, 303, 307, 308])
@pytest.mark.parametrize('destination', [
    'file:///tmp/example.txt', 'data:text/plain,hello', 'ftp://example.invalid/a',
])
async def test_redirect_non_http_scheme_is_a_plain_error_without_following(code, destination, monkeypatch):
    calls, responses = redirect_transport(monkeypatch, destination, code)
    node, ctx, _, done, errors = runner('http_request_node', dict(url='https://example.invalid/start'))
    await node.execute(ctx)
    assert not done and len(errors) == 1
    assert errors[0].code == 'unsupported_url_scheme'
    assert str(errors[0]) == 'Only http:// and https:// URLs are supported.'
    assert calls == ['https://example.invalid/start']
    assert responses[0].closed


@pytest.mark.asyncio
@pytest.mark.parametrize('code', [301, 302, 303, 307, 308])
@pytest.mark.parametrize('destination,expected', [
    ('http://example.invalid/next', 'http://example.invalid/next'),
    ('https://example.invalid/next', 'https://example.invalid/next'),
    ('/next', 'https://example.invalid/next'),
    ('//elsewhere.invalid/next', 'https://elsewhere.invalid/next'),
])
async def test_http_https_and_relative_redirects_still_work(code, destination, expected, monkeypatch):
    calls, _ = redirect_transport(monkeypatch, destination, code)
    node, ctx, _, done, errors = runner('http_request_node', dict(url='https://example.invalid/start'))
    await node.execute(ctx)
    assert not errors and done == [{'data': {'default': 'hello'}}]
    assert calls == ['https://example.invalid/start', expected]


@pytest.mark.asyncio
async def test_later_redirect_to_data_is_rejected_after_an_allowed_hop(monkeypatch):
    calls = []
    def response(_handler, request):
        calls.append(request.full_url)
        headers = Message()
        headers['Location'] = '/next' if len(calls) == 1 else 'data:text/plain,hello'
        result = urllib.response.addinfourl(BytesIO(b''), headers, request.full_url, 302)
        result.msg = 'Redirect'
        return result
    monkeypatch.setattr(urllib.request.HTTPHandler, 'http_open', response)
    monkeypatch.setattr(urllib.request.HTTPSHandler, 'https_open', response)
    node, ctx, _, done, errors = runner('http_request_node', dict(url='https://example.invalid/start'))
    await node.execute(ctx)
    assert not done and errors[0].code == 'unsupported_url_scheme'
    assert calls == ['https://example.invalid/start', 'https://example.invalid/next']
