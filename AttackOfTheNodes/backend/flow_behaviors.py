"""Pure, shared flow declarations and graph preflight (revision 1, pass 1).

This module owns type bindings. Consumers dispatch on Kind, never on node names.
Reports describe potential arrivals, not runtime receipts or guaranteed payloads.
No mutable execution state or model calls belong here. Callers pass effective
limits; direct legacy callers resolve the persisted setting once at entry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from itertools import combinations
import re
from string import Formatter
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


def control_routes(node: Mapping[str, Any], profile: FlowProfile):
    """First wire per active output, including exclusive error recovery."""
    first = {}
    active = {port for batch in profile.batches for port in batch} | {"error"}
    for conn in node.get("connections", {}).get("outputs", []):
        port = str(conn.get("source_port") or "default")
        if port in active and port not in first:
            first[port] = (port, conn.get("target_node_id"), str(conn.get("target_port") or "input"))
    return sorted(first.values(), key=lambda edge: port_order(edge[0]))


def exclusive_routes(profile: FlowProfile, outgoing) -> set[str]:
    """Success and a wired error route are alternatives, as are route choices."""
    if profile.exclusive or "error" in outgoing:
        return {port for batch in profile.batches for port in batch} | ({"error"} if "error" in outgoing else set())
    return set()


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
        return dict(schema_version=FLOW_SCHEMA_VERSION, policy=dict(FLOW_POLICY),
                    provenance=flow_provenance(), **asdict(self))


def _compatible(a: Arrival, b: Arrival) -> bool:
    guards = dict(a.guards)
    return all(key not in guards or guards[key] == choice for key, choice in b.guards)


def analyze_flow(all_nodes: Mapping[str, dict], factory=None, *, draft: bool = False,
                 max_states: int = 20000, max_branch_depth: int | None = None) -> FlowAnalysis:
    """Shared app/authoring/drafter/trial entry point; bounded and deterministic for explicit settings.

    Draft mode adds admission gates. App mode preserves standalone joins, but
    rejects unproved/repeated collecting shapes before execution.
    Unknown payload presence is explicit; index-based resource labels are not certified.
    """
    if max_branch_depth is None:
        # Compatibility for raw coordinator callers. Validation services pass
        # their live limit explicitly, including unsaved settings overrides.
        from .configuration_manager import ConfigurationManager
        max_branch_depth = int(ConfigurationManager().get("max_branch_depth"))
    # Explicit full-or-error limit keeps both control and dependency graph
    # traversals below Python's recursion bound; no obligations are truncated.
    if len(all_nodes) > 512:
        return FlowAnalysis({}, {}, [Finding("error" if draft or any(n.get("type") == MERGE_NODE_TYPE for n in all_nodes.values()) else "warning", "flow_needs_review", "",
                            "This workflow is too large to check safely (limit: 512 nodes). Split it into smaller workflows.")], [], [])
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
    incoming_edges = {nid: [] for nid in profiles}
    for nid, data in all_nodes.items():
        edges[nid] = [edge for edge in control_routes(data, profiles[nid]) if edge[1] in profiles]
        for port, target, slot in edges[nid]:
            incoming_edges[target].append((nid, port, slot))

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
        findings.append(Finding("error" if draft or merges else "warning", "flow_needs_review", "",
                                "This workflow is too deeply connected to check safely. Split it into smaller workflows."))
        return report
    if report.back_edges:
        for mid, merge in merges.items():
            merge.shape_status = "needs_review"
            findings.append(Finding("error", "flow_needs_review", mid,
                "This Merge is connected through a loop. Remove that connection before running."))
        for source, target in report.back_edges:
            findings.append(Finding("error" if draft else "warning", "flow_loop", source,
                                    "loops are not supported in drafts yet", (source, target)))

    # Remove only DFS feedback edges from the bounded structural walk. Keep
    # the full control graph for diagnostics/dependencies and reachability.
    back_edges = set(report.back_edges)
    # Trace structural visits, retaining fork lineage and exclusive route guards.
    # A join closes the current group. Keep a path-local closed-join marker
    # until another fork opens a fresh group, without another graph traversal.
    contexts: dict[str, list[tuple]] = {nid: [] for nid in profiles}
    handoffs: dict[str, list[dict]] = {}
    ends: dict[str, list[str]] = {}
    already_joined: set[str] = set()
    stack = [(nid, None, (), (), "", None, None) for nid, p in profiles.items() if p.entry]
    # With no entry, standalone graph fixtures/fragments still get a report.
    # A disabled Branch wire must not turn its unreachable target into an entry.
    incoming = {conn.get("target_node_id") for data in all_nodes.values()
                for conn in data.get("connections", {}).get("outputs", [])}
    if not stack:
        stack.extend((nid, None, (), (), "", None, None) for nid in profiles if nid not in incoming)
    seen = set()
    while stack:
        nid, root, lineage, guards, path_name, incoming_edge, closed_join = stack.pop()
        state = (nid, root, lineage, guards, path_name, incoming_edge, closed_join)
        if state in seen:
            continue
        seen.add(state)
        if len(seen) > max_states:
            findings.append(Finding("error" if draft or merges else "warning", "flow_needs_review", nid,
                                    "This workflow has too many possible paths to check safely. Reduce the branches or split it into smaller workflows."))
            return report
        contexts[nid].append((root, lineage, guards))
        profile = profiles[nid]
        if profile.kind == Kind.JOIN:
            merge = merges[nid]
            if closed_join is not None:
                already_joined.add(nid)
            if root and root not in merge.group_roots:
                merge.group_roots.append(root)
            if incoming_edge:
                source, port, slot = incoming_edge
                arrival = Arrival(source, port, slot, lineage, path_name or name(source), guards,
                                  len(lineage), bool(guards))
                if arrival not in merge.arrivals:
                    merge.arrivals.append(arrival)
            root, lineage, path_name, closed_join = None, (), "", nid
        if profile.kind == Kind.FINISH or not edges[nid]:
            if root and lineage and lineage[0][0] == root:
                ends.setdefault(root, []).append(name(nid))
        if profile.kind == Kind.FORK:
            depth = len(lineage) + 1
            if any(port != "error" for port, _, _ in edges[nid]) and depth > max_branch_depth:
                finding = Finding("error", "branch_depth_exceeded", nid,
                    f'Branch "{name(nid)}" needs nesting depth {depth}, but the limit is {max_branch_depth}. '
                    "Reduce the nested splits or increase the branch depth limit.")
                if finding not in findings:
                    findings.append(finding)
            if root is None:
                closed_join = None
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
            if (nid, target) in back_edges:
                continue
            next_guards = guards
            # Error recovery is exclusive with successful execution, and may
            # not silently escape an expected join. Unhandled errors are not routes.
            if exclusive_routes(profile, {e[0] for e in edges[nid]}):
                # The same saved router may execute on concurrent supervisors.
                # Exclusivity belongs to a structural visit, not the saved ID.
                guard_id = nid + "@" + "/".join(f"{fork}.{p}" for fork, p in lineage)
                next_guards += ((guard_id, port if port == "error" or profile.exclusive else "success"),)
            next_lineage, next_name = lineage, path_name
            if profile.kind == Kind.FORK and port != "error":
                next_lineage += ((nid, port),)
                next_name = str((all_nodes[nid].get("config") or {}).get(f"{port}_label") or name(target))
            stack.append((target, root, next_lineage, next_guards, next_name, (nid, port, slot), closed_join))

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
            findings.append(Finding("error", "flow_needs_review", mid,
                                    "This Merge combines paths from different splits or paths already joined. Connect paths from one split to one Merge."))
        shared_split = any(other.node_id != mid and set(other.group_roots) & set(merge.group_roots)
                           for other in merges.values())
        if mid in already_joined or shared_split:
            merge.shape_status = "needs_review"
            findings.append(Finding("error", "flow_needs_review", mid,
                "This Merge joins paths that an earlier Merge already joined. Connect these paths to one Merge."
                if mid in already_joined else
                "Paths from this split reach different Merges. Connect these paths to one Merge."))
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
            choices = exclusive_routes(profile, outgoing)
            if choices:
                bad = [p for p in choices if not reaches.get(p)]
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
                                    "Use direct connections to Merge here. Join Merges are supported in the editor, but not in drafts."))
        waited = ", ".join(f"{a.path_name} ({a.slot})" for a in merge.arrivals)
        parts = [f'Merge "{name(mid)}": waits for {waited or "one incoming path"}.']
        for h in merge.handoffs:
            parts.append(f'{h["parent"]} hands off to {" and ".join(h["children"])}.')
        if merge.shape_status == "needs_review":
            parts.append("Reconnect these paths to one Merge before running.")
        elif len(shallowest_lineages) == 1:
            parts.append(f"Continues as {merge.continuation_candidates[0]}.")
        else:
            parts.append("Continues once on the path with the fewest nested splits; if tied, the path that gets here first.")
        parts.append("Output: {" + ", ".join(merge.slots) + "}.")
        for slot, schema in merge.slots.items():
            labels = list(dict.fromkeys(p["path_name"] if schema["cardinality"] == "many"
                                        else name(p["source_id"]) for p in schema["producers"]))
            if schema["cardinality"] == "many":
                parts.append(f'{slot}: list from {", ".join(labels)}, always in that order; '
                             f'read items as {{input[{slot}][0]}}, {{input[{slot}][1]}}.')
            elif len(labels) > 1:
                parts.append(f'{slot}: one of {"/".join(labels)}.')
        parts.extend(f"{ending} ends; supplies no Merge value." for ending in merge.independent_ends)
        merge.summary = " ".join(parts)

    # Only certify a direct whole-record input. Multiple possible input
    # sources, Vault selection and standalone pass-through are not proofs.
    for nid, node in all_nodes.items():
        if node.get("type") not in {"text_output_node", "concat_node"}:
            continue
        config = node.get("config") or {}
        if node.get("type") == "text_output_node" and (config.get("input_source", "Upstream payload") != "Upstream payload" or config.get("request_user_input")):
            continue
        incoming = [(source, port) for source, port, slot in incoming_edges[nid] if slot == "input"]
        if len(incoming) != 1:
            continue
        source, port = incoming[0]
        merge = merges.get(source)
        if port != "default" or merge is None or not merge.group_roots or merge.shape_status != "proved":
            continue
        template = config.get("template", "{input}")
        if not isinstance(template, str):
            continue
        try:
            fields = [field for _, field, _, _ in Formatter().parse(template) if field is not None]
        except ValueError:
            continue
        for field_name in dict.fromkeys(fields):
            match = re.match(r"^input\[(path_[a-z]+)\](?:$|[.\[])", field_name)
            if match and match[1] not in merge.slots:
                slot = match[1]
                findings.append(Finding("error", "merge_slot_unconnected", nid,
                    f'Merge "{name(source)}" input {slot} is not connected. '
                    f'Use a connected slot in the template for "{name(nid)}", or connect {slot}.',
                    (source, nid), slot, repair="Use a connected Merge slot or connect the missing input."))

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
            if target == nid or (target in reachable(nid) and nid not in reachable(target)):
                findings.append(Finding("error", "impossible_wait", nid,
                    f'Wait "{name(nid)}" depends on {"itself" if target == nid else "downstream node " + name(target)}.',
                    (nid, target), repair="Wait for a preceding node or an independently running path."))
            elif any(p.entry for p in profiles.values()) and contexts[nid] and not any(
                    target in reachable(entry) for entry, profile in profiles.items() if profile.entry):
                findings.append(Finding("error", "impossible_wait", nid,
                    f'Wait "{name(nid)}": target "{name(target)}" cannot run on an active control path.',
                    (nid, target), repair="Connect the target to an active path, or remove the wait."))
            elif contexts[nid] and contexts[target] and not any(
                    nid in reachable(source) or target in reachable(source) for source, _ in report.back_edges):
                # A disconnected control loop cannot hide this check. Only
                # contexts downstream of feedback edges are unproved visits.
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
            control_cycle = any(a in members and b in members for a, b in report.back_edges)
            if len(members) > 1 and waits and not control_cycle and not any(f.code == "impossible_wait" and f.node_id in members for f in findings):
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


class MergePlanError(ValueError):
    """The workflow cannot start because its flow has an error."""


def merge_plans_from_analysis(report: FlowAnalysis):
    """Translate the shared graph proof into run-local collector declarations.

    No graph traversal or observed-arrival inference belongs in this adapter.
    Standalone joins retain runtime pass-through; unproved group shapes cannot
    be represented as runnable plans.
    """
    from .run_context import MergePlan, MergeSlot

    error = next((f for f in report.findings if f.level == 'error'), None)
    if error:
        message = error.message
        if error.repair:
            message += ' ' + error.repair
        raise MergePlanError(message)
    plans = {}
    for mid, merge in report.merges.items():
        if merge.shape_status != 'proved':
            raise MergePlanError(f'Merge {mid} cannot combine these paths. Connect paths from one split to one Merge.')
        if not merge.group_roots:
            continue
        if len(merge.group_roots) != 1:
            raise MergePlanError(f'Merge {mid} combines different splits. Connect paths from one split to one Merge.')
        slots = {}
        for slot, schema in merge.slots.items():
            if schema['cardinality'] not in {'one', 'many'}:
                raise MergePlanError(f'Merge {mid}, input {slot}: cannot determine what this input supplies. Connect these paths to separate inputs.')
            producers = []
            for arrival in schema['producers']:
                lineage = []
                for fork, port in arrival['lineage']:
                    index = path_index(port)
                    lineage.append(index if index is not None else report.profiles[fork].ports.index(port))
                if not lineage:
                    raise MergePlanError('This Merge joins paths that an earlier Merge already joined. Connect these paths to one Merge.')
                if tuple(lineage) not in producers:
                    producers.append(tuple(lineage))
            if not producers:
                raise MergePlanError(f'Merge {mid}, input {slot}: no connected path supplies a value. Connect a path to this input.')
            slots[slot] = MergeSlot(schema['cardinality'], tuple(producers))
        plans[mid] = MergePlan(merge.group_roots[0], slots)
    return plans


FLOW_SCHEMA_VERSION = 1
FLOW_RECORD_TYPES = frozenset({'start_node','end_node','branch_node','conditional_node',
                               'branch_end_node','merge_node','wait_until_node'})
FLOW_POLICY = dict(pass_number=1, group_scope='inherited_family_in_run',
    node_completion='once_per_run_pass', branch_registration='atomic_selected_batch',
    winner='min_depth_then_arrival', continuation_depth='opening_branch_depth',
    same_slot='analysis_one_or_many')


def flow_template(node_type):
    """Bounded registry facts from this flow owner; never 64 repeated port rows."""
    if node_type not in FLOW_RECORD_TYPES:
        return None
    kind, entry = _BINDINGS[node_type]
    template = dict(schema_version=FLOW_SCHEMA_VERSION, basis='template', kind=kind.value,
                    entry=entry, pass_number=1, ports_from='resolved_output_ports')
    if kind == Kind.JOIN:
        template.update(input_ports_from='resolved_input_ports', payload='actual_deliveries_by_slot',
            slot_order='numeric', same_slot=FLOW_POLICY['same_slot'],
            dependencies='joining_paths_settled', winner=FLOW_POLICY['winner'],
            continuation_depth=FLOW_POLICY['continuation_depth'],
            completion='publish_then_complete_once', other_paths='absorbed_no_completion',
            failure='fail_once_no_partial_release_waiters', stop='quiet_cancel',
            timeout_seconds=0, no_split='actual_input_passthrough')
    elif kind == Kind.WAIT:
        template.update(payload='own_input_or_empty', dependencies='target_node_ids_completed_once',
            scope='current_run', timeout_from='timeout_seconds', unreachable='error', stop='quiet_cancel')
    elif kind == Kind.FORK:
        template.update(selection_from='branch_config', payload='input_or_port_vault_seed',
            group='inherit_else_new', handoff=FLOW_POLICY['branch_registration'],
            depth_increment=1, depth_limit='max_branch_depth', refusal='typed_error_no_children')
    elif kind == Kind.FINISH:
        template.update(ports_from=None, terminal='finish_this_path', result='return_end_once')
    elif kind == Kind.BEACON:
        template.update(payload='own_input_or_empty', join_marker='editor_wires_to_merge', barrier=False)
    elif entry:
        template.update(payload='start_rows_or_greeting', activation='always')
    else:
        template.update(payload='compared_left', activation='exactly_one', choice_ports=['true','false'])
    return template


def flow_template_problems(node_type, value):
    """Generated policy fields cannot be silently overridden by a record edit."""
    expected = flow_template(node_type)
    import json
    try:
        matches = expected is not None and value == expected and json.dumps(value,sort_keys=True,allow_nan=False) == json.dumps(expected,sort_keys=True)
    except (TypeError,ValueError):
        matches = False
    return [] if matches else ['flow_behavior: must match the versioned flow declaration']


def flow_provenance():
    """Bind exported claims to the policy and its implementation, not just prose."""
    import hashlib
    import json
    from pathlib import Path
    return dict(schema_version=FLOW_SCHEMA_VERSION,
        policy_sha256=hashlib.sha256(json.dumps(FLOW_POLICY,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        runtime_sources={name:hashlib.sha256((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in ('master_state.py','supervisor.py','run_context.py','wait_registry.py','node_base.py','node_errors.py')})


def referenced_flow(data, references):
    """Stable spec handles replace temporary ids, including ids in route guards."""
    import re
    if not references:
        return data
    pattern = re.compile(r'(?<![\w])('+'|'.join(re.escape(k) for k in references)+r')(?![\w])')
    def remap(value):
        if isinstance(value,str): return pattern.sub(lambda m:references[m[0]],value)
        if isinstance(value,dict): return {remap(k):remap(v) for k,v in value.items()}
        if isinstance(value,(tuple,list)): return [remap(v) for v in value]
        return value
    return remap(data)


def flow_brief(template):
    return {'join':'Collect joining results by slot; continue once.',
            'wait':'Wait for named steps; forward this path only.',
            'fork':'Start the chosen paths together.',
            'finish':'Finish this path.',
            'beacon':'Editor marker wired to Merge; forwards without waiting.',
            'route':'Start the run.' if template['entry'] else 'Take exactly one matching path.'}[template['kind']]
