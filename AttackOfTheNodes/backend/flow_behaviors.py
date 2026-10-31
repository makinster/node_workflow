"""Pure, shared flow declarations and graph preflight (revision 1, pass 1).

This module owns type bindings. Consumers dispatch on Kind, never on node names.
Reports describe potential arrivals, not runtime receipts or guaranteed payloads.
No mutable execution state, model calls, or persistence belongs here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from itertools import combinations
from typing import Any, Literal, Mapping

from .branch_paths import ALL_PATH_PORTS, path_index


class Kind(str, Enum):
    FORK = "fork"
    JOIN = "join"
    WAIT = "wait"
    ROUTE = "route"
    FINISH = "finish"
    BEACON = "beacon"


BRANCH_NODE_TYPE = "branch_node"
MERGE_NODE_TYPE = "merge_node"
MERGE_BEACON_TYPE = "branch_end_node"
END_NODE_TYPE = "end_node"
DEFAULT_OUTPUT_NODE_TYPES = frozenset({"end_node", "text_output_node"})

# Bindings are deliberately confined to this owner module, including debug flow.
_BINDINGS = {
    "start_node": (Kind.ROUTE, True),
    "end_node": (Kind.FINISH, False),
    "branch_node": (Kind.FORK, False),
    "branch_end_node": (Kind.BEACON, False),
    "conditional_node": (Kind.ROUTE, False),
    "if_changed_node": (Kind.ROUTE, False),
    "random_branch_node": (Kind.ROUTE, False),
    "deep_branch_node": (Kind.FORK, False),
    "merge_node": (Kind.JOIN, False),
    "wait_until_node": (Kind.WAIT, False),
    "error_mux_node": (Kind.ROUTE, False),
}


def parse_targets(raw: Any) -> tuple[str, ...]:
    """The existing Wait Until list/comma/newline grammar, with stable dedup."""
    items = raw if isinstance(raw, list) else str(raw or "").replace("\n", ",").split(",")
    return tuple(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))


def port_order(port: str) -> tuple[int, str]:
    index = path_index(port)
    return (index if index is not None else len(ALL_PATH_PORTS), port)


@dataclass(frozen=True)
class FlowProfile:
    kind: Kind = Kind.ROUTE
    entry: bool = False
    ports: tuple[str, ...] = ("default",)
    # Each batch is an alternative; ports within a batch are concurrent.
    batches: tuple[tuple[str, ...], ...] = (("default",),)
    targets: tuple[str, ...] = ()
    input_ports: tuple[str, ...] = ()
    schema_version: int = 1
    pass_number: int = 1
    group_scope: Literal["inherited_family_in_run"] = "inherited_family_in_run"
    node_completion: Literal["once_per_run_pass"] = "once_per_run_pass"
    branch_registration: Literal["atomic_selected_batch"] = "atomic_selected_batch"
    winner: Literal["min_depth_then_arrival"] = "min_depth_then_arrival"
    same_slot: Literal["analysis_one_or_many"] = "analysis_one_or_many"

    def __post_init__(self):
        expected = {"group_scope": "inherited_family_in_run",
                    "node_completion": "once_per_run_pass",
                    "branch_registration": "atomic_selected_batch",
                    "winner": "min_depth_then_arrival", "same_slot": "analysis_one_or_many"}
        if not isinstance(self.kind, Kind) or self.schema_version != 1 or self.pass_number != 1:
            raise ValueError("Unsupported flow profile version, pass or kind")
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Unsupported flow policy")

    @property
    def exclusive(self) -> bool:
        return len(self.batches) > 1


def resolve_flow(node: Mapping[str, Any], factory=None) -> FlowProfile:
    """Resolve actual active ports and legacy Branch choices without defaults injection."""
    if factory is None:
        from .node_factory import NodeFactory
        factory = NodeFactory()
    node_type = str(node.get("type") or "")
    kind, entry = _BINDINGS.get(node_type, (Kind.ROUTE, False))
    if factory.spawns_branches(node_type):
        kind = Kind.FORK
    ports = tuple(factory.node_output_ports(node))
    inputs = tuple(factory.node_input_ports(node))
    config = node.get("config") or {}
    if node_type not in _BINDINGS:
        meta = factory.metadata_for_type(node_type) or {}
        if meta.get("terminates_branch"):
            kind = Kind.FINISH
    if kind == Kind.FINISH:
        ports, batches = (), ()
    elif kind == Kind.FORK:
        batches = (ports,)
        if node_type == "branch_node" and "branch_count" not in config:
            condition = config.get("condition", "always_branch")
            if condition in {"path_a_only", "path_b_only"}:
                batches = (("path_a" if condition == "path_a_only" else "path_b",),)
            elif condition == "string_match":
                choices = []
                for key, fallback in (("on_match", "path_a"), ("on_no_match", "path_b")):
                    value = config.get(key)
                    choices.append(value if value in ALL_PATH_PORTS else fallback)
                batches = tuple(dict.fromkeys((p,) for p in choices))
    elif node_type in {"conditional_node", "random_branch_node", "if_changed_node"}:
        batches = tuple((p,) for p in ports)
    elif node_type == "error_mux_node":
        from .node_errors import mux_routes, mux_has_unmatched_route
        active = {"default"} | {route["id"] for route in mux_routes(config) if route["codes"]}
        if mux_has_unmatched_route(config):
            active.add("unmatched")
        batches = tuple((p,) for p in ports if p in active)
    else:
        ports = tuple(p for p in ports if p == "default")
        batches = (ports,)
    return FlowProfile(kind=kind, entry=entry, ports=ports, batches=batches,
                       targets=parse_targets(config.get("target_node_ids")) if kind == Kind.WAIT else (),
                       input_ports=inputs)


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    node_id: str
    message: str
    path: tuple[str, ...] = ()
    slot: str = ""
    route: str = ""
    repair: str = ""


@dataclass(frozen=True)
class Arrival:
    source_id: str
    source_port: str
    slot: str
    lineage: tuple[tuple[str, str], ...]
    path_name: str
    guards: tuple[tuple[str, str], ...]
    depth: int
    if_it_runs: bool
    presence: str = "possible_missing"


@dataclass
class MergeAnalysis:
    node_id: str
    group_roots: list[str] = field(default_factory=list)
    pass_number: int = 1
    arrivals: list[Arrival] = field(default_factory=list)
    slots: dict[str, dict] = field(default_factory=dict)
    handoffs: list[dict] = field(default_factory=list)
    independent_ends: list[str] = field(default_factory=list)
    continuation_candidates: list[str] = field(default_factory=list)
    continuation_policy: str = "min_depth_then_arrival"
    admission_stage: int = 1
    summary: str = ""
    shape_status: str = "proved"


@dataclass
class FlowAnalysis:
    profiles: dict[str, FlowProfile]
    merges: dict[str, MergeAnalysis]
    findings: list[Finding]
    dependencies: list[dict]
    back_edges: list[tuple[str, str]]
    admission_stage: int = 1
    groups: dict[str, dict] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return not any(f.level == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return asdict(self)


def _compatible(a: Arrival, b: Arrival) -> bool:
    guards = dict(a.guards)
    return all(key not in guards or guards[key] == choice for key, choice in b.guards)


def analyze_flow(all_nodes: Mapping[str, dict], factory=None, *, draft: bool = False,
                 max_states: int = 20000) -> FlowAnalysis:
    """Shared app/authoring/drafter/trial entry point; bounded, deterministic, pure.

    Draft mode adds unsupported-shape gates. App mode preserves standalone and
    repeated hand-built joins, while still rejecting unsafe joins and deadlocks.
    Unknown payload presence is explicit; index-based resource labels are not certified.
    """
    # Explicit full-or-error limit keeps both control and dependency graph
    # traversals below Python's recursion bound; no obligations are truncated.
    if len(all_nodes) > 512:
        return FlowAnalysis({}, {}, [Finding("error" if draft else "warning", "flow_needs_review", "",
                            "Flow graph exceeds the 512-node analysis limit; needs review.")], [], [])
    if factory is None:
        from .node_factory import NodeFactory
        factory = NodeFactory()
    profiles = {nid: resolve_flow(data, factory) for nid, data in all_nodes.items()}
    findings: list[Finding] = []
    merges = {nid: MergeAnalysis(nid) for nid, p in profiles.items() if p.kind == Kind.JOIN}
    report = FlowAnalysis(profiles, merges, findings, [], [])
    name = lambda nid: str(all_nodes[nid].get("alias") or nid)
    # The engine follows the first wire on each fired output, not every wire.
    edges: dict[str, list[tuple[str, str, str]]] = {}
    for nid, data in all_nodes.items():
        first = {}
        for conn in data.get("connections", {}).get("outputs", []):
            port = str(conn.get("source_port") or "default")
            if port not in first:
                first[port] = (port, conn.get("target_node_id"), str(conn.get("target_port") or "input"))
        active = {port for batch in profiles[nid].batches for port in batch}
        edges[nid] = [edge for port, edge in first.items()
                      if (port in active or port == "error") and edge[1] in profiles]
        edges[nid].sort(key=lambda e: port_order(e[0]))

    def reachable(start, stop=None):
        seen, stack = set(), [start]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            if current != stop:
                stack.extend(e[1] for e in edges.get(current, ()))
        return seen

    # Recognise genuine control loops before adding completion dependencies.
    colour = {}
    def visit(nid):
        colour[nid] = 1
        for _, target, _ in edges[nid]:
            if colour.get(target) == 1:
                report.back_edges.append((nid, target))
            elif target not in colour:
                visit(target)
        colour[nid] = 2
    try:
        for nid in sorted(profiles):
            if nid not in colour:
                visit(nid)
    except RecursionError:
        findings.append(Finding("error" if draft else "warning", "flow_needs_review", "",
                                "Flow graph exceeds analysis depth; needs review."))
        return report
    if report.back_edges:
        for source, target in report.back_edges:
            findings.append(Finding("error" if draft else "warning", "flow_loop", source,
                                    "loops are not supported in drafts yet", (source, target)))
        return report

    # Trace structural visits, retaining fork lineage and exclusive route guards.
    # A join settles these incoming lineages, retaining the inherited root.
    # Repeated joins are reported as needs_review rather than guessing a winner.
    contexts: dict[str, list[tuple]] = {nid: [] for nid in profiles}
    handoffs: dict[str, list[dict]] = {}
    ends: dict[str, list[str]] = {}
    stack = [(nid, None, (), (), "", None) for nid, p in profiles.items() if p.entry]
    # With no entry, standalone graph fixtures/fragments still get a report.
    # A disabled Branch wire must not turn its unreachable target into an entry.
    incoming = {conn.get("target_node_id") for data in all_nodes.values()
                for conn in data.get("connections", {}).get("outputs", [])}
    if not stack:
        stack.extend((nid, None, (), (), "", None) for nid in profiles if nid not in incoming)
    seen = set()
    while stack:
        nid, root, lineage, guards, path_name, incoming_edge = stack.pop()
        state = (nid, root, lineage, guards, path_name, incoming_edge)
        if state in seen:
            continue
        seen.add(state)
        if len(seen) > max_states:
            findings.append(Finding("error" if draft else "warning", "flow_needs_review", nid,
                                    "Flow graph exceeds the analysis state bound; needs review."))
            return report
        contexts[nid].append((root, lineage, guards))
        profile = profiles[nid]
        if profile.kind == Kind.JOIN:
            merge = merges[nid]
            if root and root not in merge.group_roots:
                merge.group_roots.append(root)
            if incoming_edge:
                source, port, slot = incoming_edge
                arrival = Arrival(source, port, slot, lineage, path_name or name(source), guards,
                                  len(lineage), bool(guards))
                if arrival not in merge.arrivals:
                    merge.arrivals.append(arrival)
            lineage, path_name = (), ""
        if profile.kind == Kind.FINISH or not edges[nid]:
            if root and lineage and lineage[0][0] == root:
                ends.setdefault(root, []).append(name(nid))
        if profile.kind == Kind.FORK:
            root = root or nid
            children = [e for e in edges[nid] if e[0] != "error"]
            handoff = {"node_id": nid, "parent": path_name or name(nid),
                       "children": [name(e[1]) for e in children], "lineage": lineage,
                       "if_it_runs": bool(guards), "registration": "atomic_selected_batch"}
            if handoff not in handoffs.setdefault(root, []):
                handoffs[root].append(handoff)
            group = report.groups.setdefault(root, {"root": root, "pass": 1,
                "scope": "inherited_family_in_run", "members": [], "handoffs": [], "independent_ends": []})
            for port, target, _ in children:
                member = {"lineage": lineage + ((nid, port),), "path_name": name(target),
                          "depth": len(lineage) + 1, "if_it_runs": bool(guards) or profile.exclusive,
                          "selection": profile.batches, "fork_node_id": nid, "port": port}
                if member not in group["members"]:
                    group["members"].append(member)
        for port, target, slot in reversed(edges[nid]):
            next_guards = guards
            # Error recovery is exclusive with successful execution, and may
            # not silently escape an expected join. Unhandled errors are not routes.
            if profile.exclusive or any(e[0] == "error" for e in edges[nid]):
                # The same saved router may execute on concurrent supervisors.
                # Exclusivity belongs to a structural visit, not the saved ID.
                guard_id = nid + "@" + "/".join(f"{fork}.{p}" for fork, p in lineage)
                next_guards += ((guard_id, port if port == "error" or profile.exclusive else "success"),)
            next_lineage, next_name = lineage, path_name
            if profile.kind == Kind.FORK and port != "error":
                next_lineage += ((nid, port),)
                next_name = str((all_nodes[nid].get("config") or {}).get(f"{port}_label") or name(target))
            stack.append((target, root, next_lineage, next_guards, next_name, (nid, port, slot)))

    for root, group in report.groups.items():
        group["handoffs"] = handoffs.get(root, [])
        group["independent_ends"] = list(dict.fromkeys(ends.get(root, [])))

    for mid, merge in merges.items():
        merge.arrivals.sort(key=lambda a: (tuple((fork, port_order(port)) for fork, port in a.lineage),
                                           a.guards, a.source_id, port_order(a.slot)))
        if not merge.group_roots and (draft or contexts[mid]):
            findings.append(Finding("error" if draft else "warning", "merge_outside_split", mid,
                                    f'Merge "{name(mid)}" is outside a split; it passes through one arrival.',
                                    repair="Place the Merge after parallel paths from a split."))
        if len(merge.group_roots) > 1 or (merge.group_roots and any(not a.lineage for a in merge.arrivals)):
            merge.shape_status = "needs_review"
            findings.append(Finding("error" if draft else "warning", "flow_needs_review", mid,
                                    "Merge receives unrelated groups or an arrival outside its family; shape needs review."))
        prior_joins = [other for other in merges if other != mid and mid in reachable(other)]
        if prior_joins:
            merge.shape_status = "needs_review"
            findings.append(Finding("error" if draft else "warning", "flow_needs_review", mid,
                "Repeated joins retain their inherited family, but their arrival shape needs review."))
        for root in merge.group_roots:
            merge.handoffs.extend(h for h in handoffs.get(root, [])
                                  if h["node_id"] != root and mid in reachable(h["node_id"], mid))
            merge.independent_ends.extend(dict.fromkeys(ends.get(root, [])))
        for slot in sorted({a.slot for a in merge.arrivals}, key=port_order):
            arrivals = [a for a in merge.arrivals if a.slot == slot]
            concurrent = any(a.lineage != b.lineage and _compatible(a, b)
                             for a, b in combinations(arrivals, 2))
            merge.slots[slot] = {"cardinality": ("many" if concurrent else "one") if merge.shape_status == "proved" else None,
                                 "producers": [asdict(a) for a in arrivals],
                                 "presence": "possible_missing", "omit_if_no_present_values": True,
                                 "order": "structural_path_lineage", "index_labels_certified": False}
        shallowest_lineages = set()
        if merge.arrivals and merge.shape_status == "proved":
            depth = min(a.depth for a in merge.arrivals)
            merge.continuation_candidates = list(dict.fromkeys(a.path_name for a in merge.arrivals if a.depth == depth))
            shallowest_lineages = {a.lineage for a in merge.arrivals if a.depth == depth}
        # A route on a required path must lead to the Merge in every alternative.
        for nid, profile in profiles.items():
            if nid == mid or not (nid in merge.group_roots or any(root in merge.group_roots for root, _, _ in contexts[nid])):
                continue
            outgoing = {port: target for port, target, _ in edges[nid]}
            reaches = {port: mid in reachable(target, mid) for port, target in outgoing.items()}
            if not any(reaches.values()):
                continue
            alternatives = {p for batch in profile.batches for p in batch}
            if profile.exclusive or "error" in outgoing:
                bad = [p for p in alternatives | ({"error"} if "error" in outgoing else set()) if not reaches.get(p)]
                for port in sorted(bad, key=port_order):
                    slots = tuple(sorted({a.slot for a in merge.arrivals
                                          if any(f.split("@", 1)[0] == nid for f, _ in a.guards)}, key=port_order))
                    findings.append(Finding("error", "merge_required_path_escape", mid,
                        f'Merge "{name(mid)}" waits for path through "{name(nid)}" '
                        f'({", ".join(slots)}), but route {port} leads away from it.',
                        (nid, outgoing.get(port, "unconnected")), ", ".join(slots), port,
                        "Reconnect every alternative to the same Merge slot, or remove this required join."))
                # A conditional fork cannot omit a required wired slot; exclusive
                # alternatives to one slot are explicitly safe.
                if profile.kind == Kind.FORK and not bad:
                    slots_by_choice = [{a.slot for a in merge.arrivals if any(f.split("@", 1)[0] == nid and choice == p for f, choice in a.guards)}
                                       for p in sorted(alternatives)]
                    if slots_by_choice and any(s != slots_by_choice[0] for s in slots_by_choice[1:]):
                        findings.append(Finding("error", "merge_required_child_omitted", mid,
                            f'Merge "{name(mid)}": conditional split "{name(nid)}" may not launch a required wired path.',
                            (nid,), repair="Rejoin exclusive alternatives through the same slot."))
        if any(a.depth > 1 or a.guards for a in merge.arrivals) or any(s["cardinality"] == "many" for s in merge.slots.values()):
            merge.admission_stage = 2
        if any(profiles[a.source_id].kind == Kind.BEACON for a in merge.arrivals) and draft:
            findings.append(Finding("error", "flow_needs_review", mid,
                                    "Merge Beacon wiring is supported in the editor, outside draft admission."))
        waited = ", ".join(f"{a.path_name} ({a.slot})" for a in merge.arrivals)
        parts = [f'Merge "{name(mid)}": waits for {waited or "one incoming path"}.']
        for h in merge.handoffs:
            parts.append(f'{h["parent"]} hands off to {" and ".join(h["children"])}.')
        if merge.shape_status == "needs_review":
            parts.append("Continuation and output shape need review.")
        elif len(shallowest_lineages) == 1:
            parts.append(f"Continues as {merge.continuation_candidates[0]}.")
        else:
            parts.append("Continues as the first arrival at the shallowest depth.")
        parts.append("Output: {" + ", ".join(merge.slots) + "}.")
        for slot, schema in merge.slots.items():
            labels = list(dict.fromkeys(p["path_name"] if schema["cardinality"] == "many"
                                        else name(p["source_id"]) for p in schema["producers"]))
            if schema["cardinality"] == "many":
                parts.append(f'{slot}: list from {", ".join(labels)}.')
            elif len(labels) > 1:
                parts.append(f'{slot}: one of {"/".join(labels)}.')
        parts.extend(f"{ending} ends; supplies no Merge value." for ending in merge.independent_ends)
        merge.summary = " ".join(parts)

    for mid, merge in merges.items():
        for arrival in merge.arrivals:
            report.dependencies.append({"source": arrival.source_id, "target": mid,
                "event": "group_member_arrived", "slot": arrival.slot,
                "lineage": arrival.lineage, "pass": 1})

    # Edges point from prerequisite to dependent completion. Every Merge also
    # depends on all potential producers, not merely its first incoming wire.
    dependencies = {nid: set() for nid in profiles}
    for source, outgoing in edges.items():
        for _, target, _ in outgoing:
            dependencies[source].add(target)
            report.dependencies.append({"source": source, "target": target, "event": "control", "pass": 1})
    for nid, p in profiles.items():
        for target in p.targets:
            if target not in profiles:
                findings.append(Finding("error", "wait_target_missing", nid,
                                        f'Wait "{name(nid)}" targets missing node {target}.'))
                continue
            dependencies[target].add(nid)
            report.dependencies.append({"source": target, "target": nid, "event": "node_completed_once", "pass": 1})
            if target == nid or target in reachable(nid):
                findings.append(Finding("error", "impossible_wait", nid,
                    f'Wait "{name(nid)}" depends on {"itself" if target == nid else "downstream node " + name(target)}.',
                    (nid, target), repair="Wait for a preceding node or an independently running path."))
            elif any(p.entry for p in profiles.values()) and contexts[nid] and not contexts[target]:
                findings.append(Finding("error", "impossible_wait", nid,
                    f'Wait "{name(nid)}": target "{name(target)}" cannot run on an active control path.',
                    (nid, target), repair="Connect the target to an active path, or remove the wait."))
            elif contexts[nid] and contexts[target]:
                # A target behind a mutually exclusive route is not guaranteed.
                safe = all(any(all(k in dict(wg) and dict(wg)[k] == v for k, v in tg)
                                   for _, _, tg in contexts[target]) for _, _, wg in contexts[nid])
                if not safe:
                    findings.append(Finding("error" if draft else "warning", "wait_target_needs_review", nid,
                        f'Wait "{name(nid)}": target "{name(target)}" is behind an exclusive route; completion needs review.'))
    # Tarjan SCC over control plus completion dependencies catches mutual and
    # cross-path cycles without declaring valid cross-path gates impossible.
    index, indices, low, active, on_stack = 0, {}, {}, [], set()
    def component(nid):
        nonlocal index
        indices[nid] = low[nid] = index
        index += 1
        active.append(nid)
        on_stack.add(nid)
        for target in sorted(dependencies[nid]):
            if target not in indices:
                component(target)
                low[nid] = min(low[nid], low[target])
            elif target in on_stack:
                low[nid] = min(low[nid], indices[target])
        if low[nid] == indices[nid]:
            members = []
            while True:
                member = active.pop()
                on_stack.remove(member)
                members.append(member)
                if member == nid:
                    break
            waits = [m for m in members if profiles[m].kind == Kind.WAIT]
            if len(members) > 1 and waits and not any(f.code == "impossible_wait" and f.node_id in members for f in findings):
                findings.append(Finding("error", "impossible_wait", sorted(waits)[0],
                    "Impossible completion wait cycle: " + ", ".join(name(m) for m in sorted(members)) + ".",
                    tuple(sorted(members)), repair="Remove a completion dependency from this cycle."))
    for nid in sorted(profiles):
        if nid not in indices:
            component(nid)
    if any(p.kind == Kind.WAIT for p in profiles.values()):
        report.admission_stage = 2
    for merge in merges.values():
        report.admission_stage = max(report.admission_stage, merge.admission_stage)
        later = ((reachable(merge.node_id) & merges.keys()) - {merge.node_id}) | {
            other.node_id for other in merges.values() if other.node_id != merge.node_id
            and set(other.group_roots) & set(merge.group_roots)}
        if draft and later:
            findings.append(Finding("error", "repeated_join_unsupported", merge.node_id,
                                    "Drafts allow at most one Merge per group until repeated joins are tested."))
    return report


def reached_with_open_family(all_nodes: Mapping[str, dict], target: str, factory=None) -> bool:
    """A join settles the inherited family, including nested handoffs."""
    profiles = {nid: resolve_flow(data, factory) for nid, data in all_nodes.items()}
    stack = [(nid, False) for nid, profile in profiles.items() if profile.entry]
    seen = set()
    while stack:
        nid, opened = stack.pop()
        if (nid, opened) in seen:
            continue
        seen.add((nid, opened))
        profile = profiles[nid]
        if profile.kind == Kind.JOIN:
            opened = False
        if nid == target and opened:
            return True
        if profile.kind == Kind.FORK:
            opened = True
        active = {p for batch in profile.batches for p in batch} | {"error"}
        used = set()
        for edge in all_nodes[nid].get("connections", {}).get("outputs", []):
            port = edge.get("source_port", "default")
            nxt = edge.get("target_node_id")
            if port in active and port not in used and nxt in profiles:
                stack.append((nxt, opened))
                used.add(port)
    return False
