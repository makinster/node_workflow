"""Named notification helpers for common frontend outcomes."""

from __future__ import annotations

from typing import Any


def notify_info(app: Any, message: str) -> None:
    """Show a standard informational notification."""
    app.notify(message)
    restore_editor_focus(app)


def notify_error(app: Any, message: str) -> None:
    """Show a standard error notification."""
    app.notify(message, severity="error")
    restore_editor_focus(app)


def restore_editor_focus(app: Any) -> None:
    """Restore editor list focus after transient notifications."""
    def restore() -> None:
        try:
            from frontend.screens.editor import EditorScreen

            candidates = [app.screen]
            try:
                candidates.append(app.query_one(EditorScreen))
            except Exception:
                pass
            for candidate in candidates:
                restore_focus = getattr(candidate, "_restore_node_list_focus", None)
                if restore_focus is not None:
                    restore_focus()
                    break
        except Exception:
            return

    restore()
    try:
        app.call_after_refresh(restore)
    except Exception:
        pass
    try:
        app.call_later(restore)
    except Exception:
        pass
    try:
        app.set_timer(0.01, restore)
    except Exception:
        pass


def workflow_saved(app: Any) -> None:
    notify_info(app, "Workflow saved")


def workflow_already_running(app: Any) -> None:
    notify_info(app, "Workflow is already running")


def workflow_start_failed(app: Any) -> None:
    notify_error(app, "Workflow did not start")


def workflow_stopped(app: Any) -> None:
    notify_info(app, "Workflow stopped")


def workflow_created(app: Any) -> None:
    notify_info(app, "New workflow created")


def workflow_loaded(app: Any, workflow_name: str) -> None:
    notify_info(app, f"Loaded {workflow_name}")


def workflow_load_failed(app: Any) -> None:
    notify_error(app, "Workflow could not be loaded")


def workflow_duplicated(app: Any) -> None:
    notify_info(app, "Workflow duplicated")


def workflow_deleted(app: Any, deleted: bool) -> None:
    notify_info(app, "Workflow deleted" if deleted else "Workflow was not found")


def workflow_imported(app: Any) -> None:
    notify_info(app, "Workflow imported")


def workflow_import_failed(app: Any, message: str | None = None) -> None:
    notify_error(app, message or "Workflow could not be imported")


def workflow_exported(app: Any, path: str, exported: bool) -> None:
    notify_info(
        app,
        f"Exported workflow to {path}" if exported else "Workflow could not be exported",
    )


def workflow_export_failed(app: Any, error: Exception) -> None:
    notify_error(app, f"Export failed: {error}")


def missing_service(app: Any, action: str, service: str = "SaveManager") -> None:
    notify_error(app, f"{action} requires {service}")


def settings_unavailable(app: Any) -> None:
    notify_error(app, "Settings are unavailable")


def settings_saved(app: Any) -> None:
    notify_info(app, "Settings saved")


def workflow_valid(app: Any) -> None:
    notify_info(app, "Workflow is valid")


def no_node_selected(app: Any) -> None:
    notify_info(app, "No node selected")


def breakpoint_toggled(app: Any, enabled: bool) -> None:
    notify_info(app, "Breakpoint set" if enabled else "Breakpoint cleared")


def breakpoints_cleared(app: Any, count: int) -> None:
    notify_info(app, f"Cleared {count} breakpoint{'s' if count != 1 else ''}")


def cannot_delete_start_node(app: Any) -> None:
    notify_error(app, "Cannot delete the Start node")


def cannot_delete_structural_node(app: Any) -> None:
    notify_error(app, "Branch and merge structure must be rewired before deletion")


def node_deleted(app: Any) -> None:
    notify_info(app, "Node deleted - open the stub to choose a replacement")


def tombstone_removed(app: Any) -> None:
    notify_info(app, "Deleted node stub removed")


def branch_pruned(app: Any, kept_label: str, pruned_count: int) -> None:
    suffix = f" ({pruned_count} node{'s' if pruned_count != 1 else ''} removed)"
    notify_info(app, f"Kept '{kept_label}'{suffix}")


def node_replaced(app: Any, node_type: str) -> None:
    notify_info(app, f"Node replaced with {node_type}")


def unknown_node_type(app: Any, node_type: str) -> None:
    notify_error(app, f"Unknown node type: {node_type}")


def node_added(app: Any, inserted: bool = False) -> None:
    notify_info(app, "Node inserted" if inserted else "Node added")


def node_updated(app: Any) -> None:
    notify_info(app, "Node updated")


def jumped_to_node(app: Any, node_id: str) -> None:
    notify_info(app, f"Jumped to {node_id}")


def viewing_branch(app: Any, branch_label: str) -> None:
    notify_info(app, f"Viewing branch: {branch_label}")


def no_run_errors(app: Any) -> None:
    notify_info(app, "No errors for this run")
