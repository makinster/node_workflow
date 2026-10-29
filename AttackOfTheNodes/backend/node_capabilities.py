"""Standard routing options verified by the executable claims suite.

Saved defaults do not implement an option. Unsupported options stay explicit;
no metadata record is weakened to hide them.
"""
STANDARD_FLAGS = frozenset({
    'vault_write', 'transient_output', 'dead_drop_passthrough', 'transient_outputs',
})
# Owner decision: this fixed-forwarding action never suppresses its file reference.
UNSUPPORTED_SUPPRESSION = frozenset({'window_control_node'})


def supported_standard_flags(metadata, config=None):
    kind = metadata.get('type')
    default = (metadata.get('output_port_metadata') or {}).get('default') or {}
    supported = set()
    if 'vault' in (default.get('to') or []):
        supported.add('vault_write')
    if ('transient_output' in (metadata.get('default_config') or {})
            and kind not in UNSUPPORTED_SUPPRESSION):
        supported.add('transient_output')
    if default.get('pass_through'):
        supported.add('dead_drop_passthrough')
    # No execute/supervisor consumes transient_outputs; never advertise it.
    if kind == 'start_node' and config and (config.get('rows') or config.get('no_inputs')):
        supported -= {'vault_write', 'transient_output'}
    return frozenset(supported)
