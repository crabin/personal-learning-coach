"""Tests for the JSON persistence layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_learning_coach.data_store import _Store, user_profiles
from personal_learning_coach.models import DomainEnrollment, UserProfile


def test_save_and_get(tmp_data_dir: Path) -> None:
    profile = UserProfile(name="Bob")
    store = _Store("user_profiles.json", UserProfile)
    store.save(profile)
    fetched = store.get(profile.user_id)
    assert fetched is not None
    assert fetched.name == "Bob"


def test_all_returns_list(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    store.save(UserProfile(name="Alice"))
    store.save(UserProfile(name="Bob"))
    records = store.all()
    assert len(records) == 2


def test_get_missing_returns_none(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    assert store.get("nonexistent") is None


def test_missing_file_returns_empty(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    assert store.all() == []


def test_delete(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    profile = UserProfile(name="Carol")
    store.save(profile)
    assert store.delete(profile.user_id) is True
    assert store.get(profile.user_id) is None


def test_delete_missing_returns_false(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    assert store.delete("does-not-exist") is False


def test_filter_by_field(tmp_data_dir: Path) -> None:
    store = _Store("domain_enrollments.json", DomainEnrollment)
    e1 = DomainEnrollment(user_id="u1", domain="ai_agent")
    e2 = DomainEnrollment(user_id="u2", domain="python")
    store.save(e1)
    store.save(e2)
    results = store.filter(user_id="u1")
    assert len(results) == 1
    assert results[0].domain == "ai_agent"


def test_save_overwrites_existing(tmp_data_dir: Path) -> None:
    store = _Store("user_profiles.json", UserProfile)
    profile = UserProfile(name="Dave")
    store.save(profile)
    profile.name = "David"
    store.save(profile)
    fetched = store.get(profile.user_id)
    assert fetched is not None
    assert fetched.name == "David"
