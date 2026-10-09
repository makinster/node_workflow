"""Behavioral file track regressions: typed reads, batch atomicity and edits."""
import subprocess
from pathlib import Path
import pytest
from backend.file_refs import file_reference
from backend.file_paths import normalize_local_path
from backend.node_factory import NodeFactory
from backend.run_session import RunSession
from tests.generated.test_file_output_node import _make_context as writer_context
from tests.generated.test_file_view_node import _make_context as viewer_context


@pytest.mark.parametrize('source', ['Configured', 'Upstream payload', 'Vault'])
@pytest.mark.parametrize('content', ['', 'Unicode café\nsecond line\n'])
@pytest.mark.parametrize('transient,vault', [(True,False),(True,True),(False,True),(False,False)])
async def test_reader_copies_text_and_routes_independently(tmp_path,source,content,transient,vault):
    path=tmp_path/'read.md'; path.write_text(content,encoding='utf-8')
    ref=file_reference(str(path)); node=NodeFactory().create_node('file_reader_node','reader')
    node.config.update(input_source=source,input_vault_key='file',file_path=str(path),transient_output=transient,vault_write=vault,vault_write_key='text')
    context,done,errors=writer_context(inputs={'input':ref})
    context.memory_bank.store_persistent('file',ref,type_tag='file')
    await node.execute(context)
    assert not errors
    assert done[0]['data']==({'default':content} if transient else {})
    assert context.memory_bank.read_persistent_by_type('string')==({'text':content} if vault else {})
    assert path.read_text(encoding='utf-8')==content


async def test_reader_cached_handle_reads_current_contents(tmp_path):
    path=tmp_path/'read.txt';path.write_text('old',encoding='utf-8')
    node=NodeFactory().create_node('file_reader_node','reader');node.config['file_path']=str(path)
    session=RunSession('reader');ctx,done,errors=writer_context(run_session=session)
    try:
        await node.execute(ctx);path.write_text('new\n',encoding='utf-8');await node.execute(ctx)
        assert not errors
        assert [r['data']['default'] for r in done]==['old','new\n']
    finally: session.close_all()


@pytest.mark.parametrize('kind',['missing','directory','invalid_utf8','raw_string'])
async def test_reader_failure_publishes_nothing(tmp_path,kind):
    path=tmp_path/'file'
    if kind=='directory':path.mkdir()
    if kind=='invalid_utf8':path.write_bytes(b'\xff')
    node=NodeFactory().create_node('file_reader_node','reader');node.config.update(file_path=str(path),vault_write=True,vault_write_key='text')
    if kind=='raw_string':node.config['input_source']='Upstream payload'
    ctx,done,errors=writer_context(inputs={'input':str(path)})
    await node.execute(ctx)
    assert errors and not done
    assert ctx.memory_bank.read_persistent_by_type('string')=={}


@pytest.mark.parametrize('forward',[False,True])
async def test_manager_batch_selects_one_and_publishes_all_named_refs(tmp_path,forward):
    paths=[tmp_path/f'{i}.md' for i in range(3)]
    for p in paths:p.write_text('# title',encoding='utf-8')
    node=NodeFactory().create_node('file_view_node','manager');node.config.update(file_source='Configured',file=str(paths[0]),vault_write=True,vault_write_key='first',additional_files=[{'id':'second','path':str(paths[1]),'vault_key':''},{'id':'third','path':str(paths[2]),'vault_key':'third'}],downstream_file_id='second',dead_drop_passthrough=forward)
    ctx,done,errors,events=viewer_context(inputs={'file':'unchanged text'})
    await node.execute(ctx)
    assert not errors
    assert [event[1]['path'] for event in events]==list(map(str,paths))
    assert done[0]['data']['default']==('unchanged text' if forward else file_reference(str(paths[1])))
    assert ctx.memory_bank.read_persistent_by_type('file')=={'first':file_reference(str(paths[0])),'third':file_reference(str(paths[2]))}


@pytest.mark.parametrize('fault',['missing','duplicate_key','duplicate_id','missing_key','missing_selection'])
async def test_manager_invalid_batch_has_no_partial_publication(tmp_path,fault):
    path=tmp_path/'existing.md';path.write_text('yes',encoding='utf-8')
    row={'id':'second','path':str(path),'vault_key':'second'}
    if fault=='missing':row['path']=str(tmp_path/'absent')
    if fault=='duplicate_key':row['vault_key']='first'
    if fault=='duplicate_id':row['id']='primary'
    if fault=='missing_key':row['vault_key']=''
    node=NodeFactory().create_node('file_view_node','manager');node.config.update(file_source='Configured',file=str(path),vault_write=True,vault_write_key='first',additional_files=[row],downstream_file_id='absent' if fault=='missing_selection' else 'primary')
    ctx,done,errors,events=viewer_context();await node.execute(ctx)
    assert errors and not done and not events
    assert ctx.memory_bank.read_persistent_by_type('file')=={}


@pytest.mark.parametrize('mode',['Overwrite','Append','Prepend','Create unique'])
@pytest.mark.parametrize('interpret',[False,True])
async def test_writer_modes_preserve_boundaries_and_optional_newlines(tmp_path,mode,interpret):
    path=tmp_path/'write.txt';path.write_bytes(b'old\r\n')
    raw=r'new\n/nC:\temp'; expected='new\n\nC:\\temp' if interpret else raw
    node=NodeFactory().create_node('file_output_node','writer');node.config.update(file_path=str(path),write_mode=mode,interpret_newlines=interpret)
    ctx,done,errors=writer_context(inputs={'content':raw});await node.execute(ctx)
    assert not errors
    target=Path(done[0]['data']['default']['path'])
    output=expected+'old\r\n' if mode=='Prepend' else 'old\r\n'+expected if mode=='Append' else expected
    assert target.read_bytes()==output.encode()
    if mode=='Create unique':assert path.read_bytes()==b'old\r\n'


@pytest.mark.parametrize('content,binary,mode',[(23,False,'Overwrite'),({'type':'file'},False,'Overwrite'),('%%%%',True,'Overwrite'),('aGVsbG8=',True,'Prepend'),('text',False,'unsupported')])
async def test_writer_rejects_invalid_content_before_truncation(tmp_path,content,binary,mode):
    path=tmp_path/'safe';path.write_text('preserved',encoding='utf-8')
    node=NodeFactory().create_node('file_output_node','writer');node.config.update(file_path=str(path),binary_content=binary,write_mode=mode)
    ctx,done,errors=writer_context(inputs={'content':content});await node.execute(ctx)
    assert errors and not done and path.read_text()=='preserved'


@pytest.mark.parametrize('converted',['relative/file','user@host:/mnt/c/file','/valid\n/injected',''])
def test_path_converter_rejects_nonlocal_or_invalid_output(monkeypatch,converted):
    monkeypatch.setattr('backend.file_paths.platform.system',lambda:'Linux');monkeypatch.setattr('backend.file_paths.platform.release',lambda:'microsoft')
    monkeypatch.setattr('backend.file_paths.subprocess.run',lambda *a,**kw:subprocess.CompletedProcess(a,0,converted,''))
    with pytest.raises(ValueError):normalize_local_path(r'C:\Users\name\file')


@pytest.mark.parametrize('path',[r'C:\Users\makin\Documents\App_Tests\test.md','C:/Users/makin/Documents/App_Tests/test.md',r'\\?\C:\Users\makin\Documents\App_Tests\test.md'])
def test_path_custom_mount_and_quotes(monkeypatch,path):
    monkeypatch.setattr('backend.file_paths.platform.system',lambda:'Linux');monkeypatch.setattr('backend.file_paths.platform.release',lambda:'microsoft')
    monkeypatch.setattr('backend.file_paths.subprocess.run',lambda *a,**kw:subprocess.CompletedProcess(a,0,'/custom/drive/Unicode café.md\n',''))
    normalized=normalize_local_path('"'+path+'"')
    assert normalized==Path('/custom/drive/Unicode café.md')
    assert normalize_local_path(str(normalized))==normalized


@pytest.mark.parametrize('system',['Windows','Linux'])
def test_drive_relative_paths_rejected_on_every_runtime(monkeypatch,system):
    monkeypatch.setattr('backend.file_paths.platform.system',lambda:system)
    with pytest.raises(ValueError,match='full Windows path'):normalize_local_path('C:relative.txt')


def test_wsl_share_requires_current_distribution(monkeypatch):
    monkeypatch.setattr('backend.file_paths.platform.system',lambda:'Linux');monkeypatch.setenv('WSL_DISTRO_NAME','Ubuntu')
    assert normalize_local_path(r'\\wsl.localhost\Ubuntu\home\user\file')==Path('/home/user/file')
    with pytest.raises(ValueError,match='another'):normalize_local_path(r'\\wsl$\Debian\home\file')
