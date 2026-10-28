"""Match frozen role/route obligations without relying on node handles or aliases.

Data lineage proves which operation produced an output. Dominance and exclusive
route membership prove where that work executes. Neither replaces the other.
"""

from collections import defaultdict
from itertools import permutations


def output_ports(node):
    from backend.node_factory import NodeFactory

    return NodeFactory().node_output_ports(node)


def reachable(starts, adjacency):
    pending = list(starts)
    found = set()
    while pending:
        node = pending.pop()
        if node in found:
            continue
        found.add(node)
        pending.extend(adjacency.get(node, ()))
    return found


def graph_facts(spec):
    adjacency = defaultdict(set)
    incoming = defaultdict(set)
    routes = defaultdict(list)
    for edge in spec["connections"]:
        source, port = edge["from"].split(".", 1)
        target = edge["to"].split(".", 1)[0]
        if port == "error":
            continue
        adjacency[source].add(target)
        incoming[target].add(source)
        routes[source, port].append(target)
    starts = [
        handle for handle, node in spec["nodes"].items() if node["type"] == "start_node"
    ]
    live = reachable(starts, adjacency)
    dominators = {
        handle: ({handle} if handle in starts else set(live)) for handle in live
    }
    changed = True
    while changed:
        changed = False
        for handle in live - set(starts):
            parents = incoming[handle] & live
            common = (
                set.intersection(*(dominators[parent] for parent in parents))
                if parents
                else set()
            )
            current = {handle} | common
            if dominators[handle] != current:
                dominators[handle] = current
                changed = True
    return adjacency, routes, dominators


def selector_matches(node, selector, evidence):
    if "one_of" in selector:
        return any(
            selector_matches(node, choice, evidence) for choice in selector["one_of"]
        )
    if node["type"] != selector["type"]:
        return False
    if any(
        node["config"].get(key) != value
        for key, value in selector.get("config", {}).items()
    ):
        return False
    expressions = [output["expression"] for output in evidence]
    if "output_literal" in selector:
        return bool(expressions) and all(
            expression == ("literal", selector["output_literal"])
            for expression in expressions
        )
    if "output_operation" in selector:
        return bool(expressions) and all(
            expression[:2] == ("operation", selector["output_operation"])
            for expression in expressions
        )
    if "output_kind" in selector:
        return bool(expressions) and all(
            expression[0] == selector["output_kind"] for expression in expressions
        )
    return True


def check_required_structure(spec, declaration, results):
    from .rules import effective_nodes

    nodes = effective_nodes(spec)
    adjacency, routes, dominators = graph_facts(spec)
    visits = defaultdict(list)
    outputs = defaultdict(list)
    for result in results:
        for visit in result["visits"]:
            visits[visit["handle"]].append(visit)
        for output in result["outputs"]:
            outputs[output["handle"]].append(output)
    candidates = {
        role: [
            handle
            for handle, node in nodes.items()
            if handle in visits and selector_matches(node, selector, outputs[handle])
        ]
        for role, selector in declaration["roles"].items()
    }
    missing = [role for role, matches in candidates.items() if not matches]
    if missing:
        return dict(
            result="fail",
            problems=["missing required roles: " + ", ".join(missing)],
            candidates=candidates,
        )

    route_layout = []
    for handle, node in nodes.items():
        if node["type"] not in ("branch_node", "conditional_node"):
            continue
        ports = output_ports(node)
        descendants = {
            port: reachable(routes[handle, port], adjacency) for port in ports
        }
        for port in ports:
            siblings = set().union(
                *(descendants[other] for other in ports if other != port)
            )
            exclusive = descendants[port] - siblings
            work = sorted(
                candidate
                for candidate in exclusive
                if nodes[candidate]["type"]
                not in (
                    "start_node",
                    "end_node",
                    "branch_end_node",
                    "branch_node",
                    "conditional_node",
                )
            )
            route_layout.append(
                dict(
                    fork=handle, port=port, exclusive_nodes=sorted(exclusive), work=work
                )
            )
    empty = [route for route in route_layout if not route["work"]]
    if empty:
        return dict(
            result="fail",
            problems=[
                route["fork"] + "." + route["port"] + " has no route-local work"
                for route in empty
            ],
            routes=route_layout,
            candidates=candidates,
        )

    def relationships_hold(mapping):
        for source, target in declaration["before"] + declaration["data_from"]:
            if source not in mapping or target not in mapping:
                continue
            if mapping[source] not in dominators.get(mapping[target], set()):
                return False
        for source, target in declaration["data_from"]:
            if source in mapping and target in mapping:
                if not all(
                    mapping[source] in visit["data_lineage"]
                    for visit in visits[mapping[target]]
                ):
                    return False
        return True

    def match_routes(mapping):
        actual_forks = {
            handle
            for handle, node in nodes.items()
            if node["type"] in ("branch_node", "conditional_node")
        }
        declared_forks = {mapping[fork["role"]] for fork in declaration["forks"]}
        if actual_forks != declared_forks:
            return None
        evidence = []
        for fork in declaration["forks"]:
            handle = mapping[fork["role"]]
            ports = fork["ports"]
            if set(output_ports(nodes[handle])) != set(ports) or len(ports) != len(
                fork["work"]
            ):
                return None
            descendants = {
                port: reachable(routes[handle, port], adjacency) for port in ports
            }
            alternatives = (
                permutations(fork["work"]) if fork["permutable"] else [fork["work"]]
            )
            for groups in alternatives:
                assignment = []
                for port, roles in zip(ports, groups):
                    others = set().union(
                        *(descendants[other] for other in ports if other != port)
                    )
                    exclusive = descendants[port] - others
                    work = [mapping[role] for role in roles]
                    # Declared routes must do their own required work, never
                    # merely terminate or borrow work before/after the split.
                    if not work or not set(work).issubset(exclusive):
                        break
                    if any(handle not in dominators.get(node, set()) for node in work):
                        break
                    if any(
                        nodes[node]["type"]
                        in (
                            "start_node",
                            "end_node",
                            "branch_end_node",
                            "branch_node",
                            "conditional_node",
                        )
                        for node in work
                    ):
                        break
                    if not all(
                        any(
                            route["fork"] == handle and route["port"] == port
                            for route in visit["routes"]
                        )
                        for node in work
                        for visit in visits[node]
                    ):
                        break
                    assignment.append(
                        dict(fork=handle, port=port, roles=roles, handles=work)
                    )
                else:
                    evidence.extend(assignment)
                    break
            else:
                return None
        return evidence

    # Bound ambiguous candidate graphs instead of allowing untrusted drafts to
    # force exponential matching. Ordinary case graphs have unique candidates.
    ordered = sorted(candidates, key=lambda role: len(candidates[role]))
    attempts = 0

    def assign(mapping):
        nonlocal attempts
        if len(mapping) == len(ordered):
            route_evidence = match_routes(mapping)
            if route_evidence is not None:
                return dict(
                    result="pass",
                    roles=dict(mapping),
                    routes=route_evidence,
                    problems=[],
                )
            return None
        role = ordered[len(mapping)]
        for handle in candidates[role]:
            attempts += 1
            if attempts > 4096:
                return None
            if handle in mapping.values():
                continue
            mapping[role] = handle
            if relationships_hold(mapping):
                matched = assign(mapping)
                if matched is not None:
                    return matched
            del mapping[role]
        return None

    matched = assign({})
    if matched is not None:
        return matched
    return dict(
        result="fail",
        problems=[
            "required work is missing, on the wrong/shared route, or does not feed its declared output"
        ],
        candidates=candidates,
        routes=route_layout,
    )
