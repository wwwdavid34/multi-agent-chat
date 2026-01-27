import pytest
from unittest.mock import patch, AsyncMock, MagicMock

def test_decision_request_model():
    """DecisionRequest model should exist and accept valid input."""
    import sys
    sys.path.insert(0, "backend")
    from main import DecisionRequest
    req = DecisionRequest(thread_id="test", question="Build or buy?")
    assert req.thread_id == "test"
    assert req.constraints is None
    assert req.max_iterations == 2
    assert req.resume is False

def test_decision_request_with_all_fields():
    import sys
    sys.path.insert(0, "backend")
    from main import DecisionRequest
    req = DecisionRequest(
        thread_id="t1",
        question="Q",
        constraints={"budget": "1M"},
        max_iterations=3,
        resume=True,
        human_feedback={"action": "proceed"},
    )
    assert req.constraints == {"budget": "1M"}
    assert req.human_feedback == {"action": "proceed"}
