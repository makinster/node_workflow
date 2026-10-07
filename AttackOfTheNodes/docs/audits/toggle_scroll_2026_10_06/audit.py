"""Synthetic node configuration audit; never reads or saves owner workflows.

Run with the authoritative venv. Retains separate before/after JSON evidence.
"""

import argparse
import asyncio
import copy
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "node_config_2026_10_06"))
import capture
from textual.widgets import Checkbox, Select, SelectionList, TabPane
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.form_generator import evaluate_field_condition


def logical_visible(widget):
    return widget.display and all(a.display for a in widget.ancestors
                                 if not isinstance(a, TabPane))


def view(screen):
    scroll = screen._scroll_container()
    return {"focus": screen.app.focused.id if screen.app.focused else None,
            "scroll": float(scroll.scroll_y) if scroll else None}


def controls(screen):
    return [{"id": w.id, "disabled": w.disabled,
             "visible": logical_visible(w),
             "value": capture.clean(w.value) if hasattr(w, "value") else w.selected}
            for w in screen.query("Checkbox, Select, SelectionList") if w.id]


def check_rules(screen):
    violations = []
    values = screen._get_form_values() if screen._get_form_values else {}
    for name, rule in screen._rule_schema.items():
        condition = rule.get("visible_when")
        if condition is None:
            continue
        expected = evaluate_field_condition(condition, values)
        for suffix in (f"field-{name}", f"field-label-{name}", f"field-desc-{name}"):
            for widget in screen.query(f"#{suffix}"):
                if logical_visible(widget) != expected:
                    violations.append({"id": suffix, "expected": expected})
    return violations


async def mount(factory, meta, width):
    wm, nid, memory = capture.setup(factory, meta["type"])
    # Merge needs real synthetic branches so its conditional selector exists.
    if meta["type"] == "merge_node":
        branch = wm.add_node("branch_node")
        for port in ("path_a", "path_b"):
            beacon = wm.add_node("branch_end_node")
            wm.connect(branch, port, beacon, "input")
    original = copy.deepcopy(wm.get_node_data(nid))
    results = []
    screen = NodeConfigScreen(factory, wm, nid, wm.get_node_data(nid), memory, capture.Secrets())
    record = {"type": meta["type"], "width": width, "states": [],
              "navigation": [], "findings": [], "disabled_visible": []}
    async with capture.Harness(screen, results).run_test(size=(width, 24)) as pilot:
        await pilot.pause(.15)
        record["initial"] = view(screen)
        first = screen._keyboard_focus_widgets()
        if first and screen.app.focused is not first[0]:
            record["findings"].append({"kind": "initial_focus", "actual": view(screen)})
        scroll = screen._scroll_container()
        if scroll and scroll.scroll_y != 0:
            record["findings"].append({"kind": "initial_scroll", "actual": view(screen)})

        panes = list(screen.query(TabPane))
        for index in range(len(panes) or 1):
            if panes:
                screen.action_jump_config_tab(index + 1)
                await pilot.pause(.1)
            tab_id = panes[index].id if panes else "flat"
            widgets = screen._keyboard_focus_widgets()
            trace = []
            for _ in range(len(widgets) + 12):
                focused = screen.app.focused
                scroll = screen._scroll_container()
                trace.append(view(screen))
                if focused and scroll and screen._is_descendant_of(focused, scroll):
                    if (focused.region.y >= scroll.content_region.bottom or
                            focused.region.bottom <= scroll.content_region.y):
                        # Layout and focus scrolling can be deferred by Textual.
                        # Only report a defect that persists after settling.
                        await pilot.pause(.12)
                        if (focused.region.y >= scroll.content_region.bottom or
                                focused.region.bottom <= scroll.content_region.y):
                            record["findings"].append({"kind": "offscreen_focus", "tab": tab_id,
                                                       "actual": view(screen),
                                                       "region": list(focused.region),
                                                       "viewport": list(scroll.content_region)})
                previous = focused
                screen.action_cursor_down()
                await pilot.pause(.001)
                if screen.app.focused is previous and not isinstance(previous, SelectionList):
                    break
            for _ in range(len(widgets) + 12):
                previous = screen.app.focused
                screen.action_cursor_up()
                await pilot.pause(.001)
                trace.append(view(screen))
                if screen.app.focused is previous and not isinstance(previous, SelectionList):
                    break
            record["navigation"].append({"tab": tab_id, "trace": trace})

        ids = [w.id for w in screen.query("Checkbox, Select") if w.id]
        for wid in ids:
            widget = screen.query_one(f"#{wid}")
            before = widget.value
            choices = ([not before, before] if isinstance(widget, Checkbox) else
                       [v for _, v in widget._options if v is not Select.NULL and v != before])
            # All checkbox states at every width; select variants at 100 columns.
            if isinstance(widget, Select) and width != 100:
                continue
            for value in choices:
                widget.value = value
                await pilot.pause(.005)
                record["states"].append({"control": wid, "value": capture.clean(value),
                                         "widgets": controls(screen),
                                         "rule_violations": check_rules(screen)})
            widget.value = before
            await pilot.pause(.005)

        # Programmatic non-focused changes must not move the viewport.
        if panes:
            screen.action_jump_config_tab(1)
            await pilot.pause(.15)
        before_view = view(screen)
        for widget in screen.query("Checkbox, Select"):
            if widget is screen.app.focused or widget.disabled:
                continue
            value = widget.value
            if isinstance(widget, Checkbox):
                widget.value = not value
                await pilot.pause(.005)
                after_view = view(screen)
                if before_view != after_view:
                    record["findings"].append({"kind": "nonfocused_change_scroll", "control": widget.id,
                                               "before": before_view, "after": after_view})
                widget.value = value
                await pilot.pause(.005)
                before_view = view(screen)

        record["disabled_visible"] = [w for w in controls(screen) if w["disabled"] and w["visible"]]
        # Preserve exact saved config when cancelling after the audit mutations.
        screen.action_cancel()
        await pilot.pause(.005)
        record["cancel_unchanged"] = wm.get_node_data(nid) == original
    return record


async def main(args):
    factory = capture.NodeFactory()
    records = []
    for meta in factory.get_node_types_metadata():
        if meta["type"] == "tombstone_node":
            continue
        for width in args.widths:
            record = await mount(factory, meta, width)
            records.append(record)
        print(meta["type"], "audited", flush=True)
    summary = {"mounts": len(records), "types": len({r["type"] for r in records}),
               "widths": args.widths,
               "states": sum(len(r["states"]) for r in records),
               "navigation_samples": sum(len(n["trace"]) for r in records for n in r["navigation"]),
               "cancel_unchanged": sum(r["cancel_unchanged"] for r in records),
               "findings": [{"type": r["type"], "width": r["width"], **f} for r in records for f in r["findings"]],
               "rule_violations": [{"type": r["type"], "width": r["width"], "control": s["control"], **v}
                                   for r in records for s in r["states"] for v in s["rule_violations"]],
               "disabled_visible": [{"type": r["type"], "width": r["width"], **w}
                                    for r in records for w in r["disabled_visible"]]}
    with gzip.open(HERE / f"{args.label}_evidence.json.gz", "wt") as stream:
        json.dump(records, stream, default=str)
    (HERE / f"{args.label}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    if args.require_clean and (summary["findings"] or summary["rule_violations"] or
                               summary["disabled_visible"] or
                               summary["cancel_unchanged"] != summary["mounts"]):
        raise SystemExit("Audit has unresolved findings; see the saved summary.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="after")
    parser.add_argument("--widths", type=int, nargs="+", default=[60, 100, 140])
    parser.add_argument("--require-clean", action="store_true")
    asyncio.run(main(parser.parse_args()))
