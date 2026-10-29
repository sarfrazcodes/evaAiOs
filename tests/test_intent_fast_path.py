import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from core.eva_core.intent.matcher import IntentMatcher


def test_informational_question_uses_fast_path():
    result = IntentMatcher().match("Tell all about how to calculate a CGPA in college")
    assert result is not None
    assert result.intent == "information_request"
    assert result.confidence == 0.9