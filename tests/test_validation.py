import pytest
from datetime import datetime
from mcp_server.server import sanitize_filename, add_calendar_event, add_or_update_task, write_study_guide

def test_sanitize_filename():
    # Test normal sanitization
    assert sanitize_filename("calculus-101.md") == "calculus-101.md"
    assert sanitize_filename("study guide") == "studyguide.md"
    
    # Test directory traversal attack detection
    assert sanitize_filename("../../../etc/passwd") == "passwd.md"
    assert sanitize_filename("subfolder/../../test.txt") == "test.txt.md"

def test_add_calendar_event_validation():
    # Test invalid time format
    res = add_calendar_event("Class", "invalid-date", "2026-07-05T12:00:00")
    assert "Error: Start and end times must be in ISO format" in res
    
    # Test end time before start time
    res = add_calendar_event(
        "Study Session", 
        "2026-07-05T14:00:00", 
        "2026-07-05T13:00:00"
    )
    assert "Error: End time must be strictly after start time" in res

def test_add_task_validation():
    # Test invalid priority
    res = add_or_update_task("Do Homework", "Critical", "2026-07-10", "Todo")
    assert "Error: Priority must be" in res
    
    # Test invalid status
    res = add_or_update_task("Do Homework", "High", "2026-07-10", "Pending")
    assert "Error: Status must be" in res
    
    # Test invalid date format
    res = add_or_update_task("Do Homework", "High", "07-10-2026", "Todo")
    assert "Error: due_date must be in 'YYYY-MM-DD' format" in res
