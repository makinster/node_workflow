"""Small file/JSON nodes: real files, no model calls or owner data."""
import asyncio
import json
import os
from pathlib import Path

import pytest
from backend import text_lines, reply_shape
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_base import NodeContext
from backend.node_errors import NodeError
from backend.nodes.io.read_lines_node import ReadLinesNode
from backend.nodes.io.find_lines_node import FindLinesNode
from backend.nodes.data.check_reply_node import CheckReplyNode


@pytest.fixture
def run_node(tmp_path):
    async def run(cls, *, incoming=None, vault=None, allowed=None, **config):
        done, errors = [], []
        memory = MemoryBank(EventBus())
        for key, value in (vault or {}).items():
            memory.store_persistent(key, value, type_tag='var')
        context = NodeContext('node', 'branch', 'run', {'input': incoming}, memory,
                              done.append, errors.append, lambda _: None, lambda *_: None,
                              lambda *_: None, get_setting=lambda _: str(tmp_path) if allowed is None else allowed)
        node = cls('node', {**cls.default_config, **config})
        await node.execute(context)
        return done, errors, memory
    return run


def content(tmp_path, text):
    path = tmp_path/'sample.log'
    path.write_bytes(text.encode('utf-8'))
    return str(path)


@pytest.mark.asyncio
async def test_recent_matches_and_true_total_regression(run_node, tmp_path):
    path = content(tmp_path, ''.join(f'{n}: ERROR ERROR\n' for n in range(1, 313)))
    done, errors, memory = await run_node(FindLinesNode, file=path, input='ERROR',
        match_count_vault_write=True, match_count_vault_key='count', vault_write=True, vault_write_key='lines')
    assert not errors
    assert done[0]['data']['default'] == list(range(213, 313))
    assert memory.read_persistent('count') == 312
    assert memory.read_persistent('lines') == list(range(213, 313))
    done, errors, _ = await run_node(ReadLinesNode, file=path, input_source='Upstream payload',
                                    incoming=memory.read_persistent('lines'), lines_around=True, each_side=0)
    assert not errors and done[0]['data']['default'] == '312: ERROR ERROR\n'


@pytest.mark.asyncio
@pytest.mark.parametrize('start,end,want', [(-50,-1,'a\nb\nc'),(1,2,'a\nb\n'),(-2,-1,'b\nc'),(-9,999,'a\nb\nc')])
async def test_ranges_utf8_bom_crlf(run_node, tmp_path, start, end, want):
    path = content(tmp_path, '\ufeffa\r\nb\r\nc')
    done, errors, _ = await run_node(ReadLinesNode, file=path, input=start, to_line=end)
    assert not errors and done[0]['data']['default'] == want


@pytest.mark.asyncio
async def test_around_sources_first_last_and_empty(run_node, tmp_path):
    path = content(tmp_path, ''.join(f'{n}\n' for n in range(1, 21)))
    for source, extra in [('Upstream payload', {'incoming':[5,10]}),('Vault', {'vault':{'line':[5,10]},'input_vault_key':'line'})]:
        done, errors, _ = await run_node(ReadLinesNode, file=path, input_source=source, lines_around=True, **extra)
        assert not errors and done[0]['data']['default'] == ''.join(f'{n}\n' for n in range(5,16))
        done, errors, _ = await run_node(ReadLinesNode, file=path, input_source=source, lines_around=True, each_side=0,use_match='First',**extra)
        assert not errors and done[0]['data']['default']=='5\n'
    done, errors, _ = await run_node(ReadLinesNode,file=path,input_source='Upstream payload',incoming=[])
    assert not done and errors[0].code=='no_matches'


@pytest.mark.asyncio
@pytest.mark.parametrize('value', [True,0,'2',1.5,[True],[0],list(range(1,1002))])
async def test_bad_line_numbers(run_node,tmp_path,value):
    done,errors,_=await run_node(ReadLinesNode,file=content(tmp_path,'x\n'),input_source='Upstream payload',incoming=value)
    assert not done and errors[0].code=='invalid_range'


@pytest.mark.asyncio
async def test_line_boundaries_casefold_and_no_matches(run_node,tmp_path):
    path=content(tmp_path,'ERROR\u2028still\u0085same\nStraße\nlast\n')
    for needle,case,want in [('ERROR',True,[1]),('STRASSE',False,[2]),('STRASSE',True,[]),('[.*]',True,[])]:
        done,errors,_=await run_node(FindLinesNode,file=path,input=needle,match_case=case)
        assert not errors and done[0]['data']['default']==want
    done,errors,_=await run_node(ReadLinesNode,file=path,input=1,to_line=1)
    assert not errors and done[0]['data']['default']=='ERROR\u2028still\u0085same\n'
    empty=content(tmp_path,'')
    done,errors,_=await run_node(ReadLinesNode,file=empty)
    assert not errors and done[0]['data']['default']==''
    done,errors,_=await run_node(ReadLinesNode,file=empty,lines_around=True)
    assert not done and errors[0].code=='no_lines'


@pytest.mark.asyncio
@pytest.mark.parametrize('cls',[ReadLinesNode,FindLinesNode])
async def test_file_security_and_caps(run_node,tmp_path,cls):
    path=content(tmp_path,'ERROR\n')
    for file,extra,code in [(path,{'allowed':''},'not_allowed'),(str(tmp_path/'missing'),{},'file_missing'),
                            (str(tmp_path),{},'not_regular')]:
        done,errors,_=await run_node(cls,file=file,**extra)
        assert not done and errors[0].code==code
    os.mkfifo(tmp_path/'pipe')
    done,errors,_=await run_node(cls,file=str(tmp_path/'pipe'))
    assert not done and errors[0].code=='not_regular'
    link=tmp_path/'outside';link.symlink_to('/etc/passwd')
    done,errors,_=await run_node(cls,file=str(link))
    assert not done and errors[0].code=='not_allowed'
    Path(path).write_bytes(b'\xff\n')
    done,errors,_=await run_node(cls,file=path)
    assert not done and errors[0].code=='not_utf8'
    Path(path).write_bytes(b'x'*64001+b'\n')
    done,errors,_=await run_node(cls,file=path)
    assert not done and errors[0].code=='line_too_long'
    Path(path).write_bytes(b'x\n'*500001)
    done,errors,_=await run_node(cls,file=path,max_file_mb=1)
    assert not done and errors[0].code=='file_too_large'


@pytest.mark.asyncio
async def test_snapshot_path_race_and_mutation(run_node,tmp_path,monkeypatch):
    path=Path(content(tmp_path,'safe\n'))
    real=text_lines.checked_path
    def swap(*args,**kw):
        resolved=real(*args,**kw)
        path.unlink();path.symlink_to('/etc/passwd')
        return resolved
    monkeypatch.setattr(text_lines,'checked_path',swap)
    done,errors,_=await run_node(ReadLinesNode,file=str(path))
    assert not done and errors[0].code=='file_unreadable'
    monkeypatch.setattr(text_lines,'checked_path',real)
    path.unlink();path.write_text('safe\n')
    with pytest.raises(NodeError,match='changed'):
        with text_lines.snapshot(str(path),lambda _:str(tmp_path),10):
            path.write_text('')
    path.write_text('safe\n')
    with text_lines.snapshot(str(path),lambda _:str(tmp_path),10) as (fd,size):
        with path.open('a') as stream:stream.write('later\n')
        assert [line async for line in text_lines.lines(fd,size)]==['safe\n']


@pytest.mark.asyncio
async def test_excerpt_and_search_limits(run_node,tmp_path):
    path=content(tmp_path,'x\n'*501)
    for cfg in [{'input':1,'to_line':501},{'input':1,'to_line':2,'max_text':1}]:
        done,errors,_=await run_node(ReadLinesNode,file=path,**cfg)
        assert not done and errors[0].code=='excerpt_too_long'
    for needle in ['', 'x\ny']:
        done,errors,_=await run_node(FindLinesNode,file=path,input=needle)
        assert not done and errors[0].code=='text_missing'


@pytest.mark.asyncio
async def test_stop_closes_snapshot(tmp_path,monkeypatch):
    path=content(tmp_path,'x\n'*100000)
    close=text_lines.os.close;closed=[]
    def observed(fd):closed.append(fd);close(fd)
    monkeypatch.setattr(text_lines.os,'close',observed)
    opened=[]
    async def scan():
        with text_lines.snapshot(path,lambda _:str(tmp_path),10) as (fd,size):
            opened.append(fd)
            async for _ in text_lines.lines(fd,size):pass
    task=asyncio.create_task(scan());await asyncio.sleep(0);task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert opened and opened[0] in closed
    with pytest.raises(OSError):os.fstat(opened[0])


ROWS=[{'name':'summary','kind':'string','required':True},{'name':'cause','kind':'string','required':False}]


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['{}','[]','{"summary":false}','{"summary":"ok","cause":4}',
 '```json\n{"summary":"ok"}\n```','{"summary":"a","summary":"b"}',
 '{"summary":"ok"} trailing','{"summary":"ok","extra":null}',
 '{"summary":"ok","extra":NaN}','{"summary":"ok","extra":1e999}', '{'])
async def test_reply_mismatches(run_node,text):
    done,errors,memory=await run_node(CheckReplyNode,incoming=text,expected_fields=ROWS,dead_drop_passthrough=True,
                                     vault_write=True,vault_write_key='checked')
    assert not done and str(errors[0])=="Reply didn't match." and errors[0].code=='reply_mismatch'
    assert memory.read_persistent('checked') is None


@pytest.mark.asyncio
async def test_all_reply_types_and_sources(run_node):
    record={'s':'','n':2.5,'b':True,'a':[],'o':{},'z':None}
    rows=[{'name':name,'kind':kind,'required':True} for name,kind in zip(record,reply_shape.TYPES)]
    text=json.dumps(record)
    for source,extra in [('Configured',{'input':text}),('Upstream payload',{'incoming':text}),('Vault',{'vault':{'reply':text},'input_vault_key':'reply'})]:
        done,errors,memory=await run_node(CheckReplyNode,input_source=source,expected_fields=rows,**extra)
        assert not errors and done[0]['data']['default']==record
    assert await reply_shape.check('{"summary":"ok","extra":[]}',ROWS,extra=True)=={'summary':'ok','extra':[]}
    for text in ['{"summary":'+('['*8)+'0'+(']'*8)+'}', '{"summary":"long"}']:
        with pytest.raises(NodeError):await reply_shape.check(text,ROWS,limit=10 if 'long' in text else 64000)
    for rows in [[],[{'name':'bad name','kind':'string','required':True}],ROWS+ROWS]:
        with pytest.raises(NodeError) as error:await reply_shape.check('{}',rows)
        assert error.value.code=='shape_invalid'


@pytest.mark.asyncio
@pytest.mark.parametrize('cls,tag,value',[(ReadLinesNode,'string','ERROR\n'),(FindLinesNode,'var',[1]),(CheckReplyNode,'var',{'summary':'ok'})])
async def test_forwarding_keeps_input_identity_and_own_vault(run_node,tmp_path,cls,tag,value):
    incoming={'original':['identity']}
    cfg={'file':content(tmp_path,'ERROR\n'),'input':1,'to_line':1} if cls==ReadLinesNode else {'file':content(tmp_path,'ERROR\n'),'input':'ERROR'} if cls==FindLinesNode else {'input_source':'Configured','input':'{"summary":"ok"}','expected_fields':ROWS}
    done,errors,memory=await run_node(cls,incoming=incoming,dead_drop_passthrough=True,vault_write=True,vault_write_key='own',**cfg)
    assert not errors and done[0]['data']['default'] is incoming
    assert memory.read_persistent('own')==value
