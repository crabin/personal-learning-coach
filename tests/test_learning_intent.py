"""Tests for hidden learning intent classification."""

from __future__ import annotations

from unittest.mock import MagicMock

from personal_learning_coach.application.learning.learning_intent import classify_learning_intent


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def test_classifies_serious_domain_from_llm() -> None:
    client = _mock_client(
        """
        {
          "learning_category": "serious",
          "confidence": 0.91,
          "reason": "Technical learning goal",
          "tone_guidance": "Keep lessons structured and practical."
        }
        """
    )

    result = classify_learning_intent(
        "AI Agent",
        language="zh",
        learning_style="practice",
        preferences={},
        client=client,
    )

    assert result.learning_category == "serious"
    assert result.confidence == 0.91
    assert "structured" in result.tone_guidance


def test_classifies_playful_domain_from_llm() -> None:
    client = _mock_client(
        """
        {
          "learning_category": "playful",
          "confidence": 0.93,
          "reason": "The learner wants a humorous workplace-adjacent topic.",
          "tone_guidance": "Use imaginative examples while preserving useful skills."
        }
        """
    )

    result = classify_learning_intent(
        "上班摸鱼",
        language="zh",
        learning_style="practice",
        preferences={},
        client=client,
    )

    assert result.learning_category == "playful"
    assert result.confidence == 0.93
    assert "useful skills" in result.tone_guidance


def test_invalid_llm_json_falls_back_to_playful_keyword() -> None:
    client = _mock_client("not json")

    result = classify_learning_intent(
        "上班摸鱼",
        language="zh",
        learning_style="practice",
        preferences={},
        client=client,
    )

    assert result.learning_category == "playful"
    assert result.confidence > 0
    assert "学习价值" in result.tone_guidance


def test_low_confidence_defaults_to_serious() -> None:
    client = _mock_client(
        """
        {
          "learning_category": "playful",
          "confidence": 0.31,
          "reason": "Ambiguous",
          "tone_guidance": "Maybe playful."
        }
        """
    )

    result = classify_learning_intent(
        "沟通",
        language="zh",
        learning_style="blended",
        preferences={},
        client=client,
    )

    assert result.learning_category == "serious"
    assert result.confidence == 0.0
