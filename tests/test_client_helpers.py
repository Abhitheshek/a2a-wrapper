from a2a_wrapper._client import _extract_text_from_parts, _extract_text_from_task, _task_ids


def test_extract_text_from_parts_supports_flat_and_nested_shapes():
    parts = [
        {"text": "hello"},
        {"root": {"text": "world"}},
        {"ignored": True},
    ]

    assert _extract_text_from_parts(parts) == "hello\nworld"


def test_extract_text_from_task_prefers_status_message_then_artifacts():
    task = {
        "id": "task-1",
        "contextId": "ctx-1",
        "status": {"state": "completed", "message": {"parts": [{"text": "done"}]}},
        "artifacts": [{"parts": [{"text": "artifact text"}]}],
    }

    assert _extract_text_from_task(task) == "done"
    assert _task_ids(task) == ("task-1", "ctx-1")


def test_extract_text_from_task_falls_back_to_artifacts():
    task = {
        "id": "task-2",
        "context_id": "ctx-2",
        "status": {"state": "completed", "message": {"parts": []}},
        "artifacts": [{"parts": [{"root": {"text": "artifact fallback"}}]}],
    }

    assert _extract_text_from_task(task) == "artifact fallback"
    assert _task_ids(task) == ("task-2", "ctx-2")
