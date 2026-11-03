"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import datetime
import os
import unittest
from types import SimpleNamespace as NS

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from app.core.retention import expired_prefix

NOW = datetime.datetime(2030, 1, 1)
OLD = NOW - datetime.timedelta(days=400)


def event(created=OLD, category="A", hold=False):
    return NS(created_at=created, event_category=category, is_legal_hold=hold)


def policy(period=1, unit="Years", categories=None, hold=False):
    return NS(retention_period=period, retention_unit=unit, event_categories=categories or [], legal_hold_enabled=hold)


class ExpiredPrefixTests(unittest.TestCase):
    def test_removes_only_expired(self):
        events = [event(), event(created=NOW)]
        self.assertEqual(expired_prefix(events, [policy()], NOW), [events[0]])

    def test_stops_at_legal_hold_to_keep_chain_whole(self):
        events = [event(), event(hold=True), event()]
        self.assertEqual(expired_prefix(events, [policy()], NOW), [events[0]])

    def test_longest_matching_policy_wins(self):
        self.assertEqual(expired_prefix([event()], [policy(), policy(period=7)], NOW), [])

    def test_uncovered_event_stays(self):
        self.assertEqual(expired_prefix([event(category="B")], [policy(categories=["A"])], NOW), [])

    def test_policy_legal_hold_blocks_removal(self):
        self.assertEqual(expired_prefix([event()], [policy(hold=True)], NOW), [])
