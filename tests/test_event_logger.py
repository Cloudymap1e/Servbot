import unittest, os
from pathlib import Path
import sys

sys.path.insert(0, '/root/servbot')

from servbot.data import database as db
from servbot import event_logger as elog

TEST_DB_PATH = Path(__file__).parent / 'test_event_logger.db'

class TestEventLogger(unittest.TestCase):
    def setUp(self):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        db.DB_PATH = TEST_DB_PATH
        db.init_db()  # create base schema; event_log created lazily by elog

    def tearDown(self):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def test_log_and_query(self):
        id1 = elog.log_event('account_provision', 'success', service='db', details={'email':'a@b.com'})
        id2 = elog.log_event('email_fetch', 'error', service='imap', details={'mailbox':'a@b.com','fetched':0})
        id3 = elog.log_event('registration', 'success', service='site', details={'mailbox':'a@b.com'})
        self.assertGreater(id1, 0)
        self.assertGreater(id2, 0)
        self.assertGreater(id3, 0)

        recent = elog.get_recent_events(5)
        self.assertGreaterEqual(len(recent), 3)
        types = {r['event_type'] for r in recent}
        self.assertIn('account_provision', types)
        self.assertIn('email_fetch', types)
        self.assertIn('registration', types)

        stats = elog.get_event_stats()
        self.assertIn('by_type', stats)
        self.assertIn('by_status', stats)
        self.assertGreaterEqual(stats['by_type'].get('account_provision', 0), 1)
        self.assertGreaterEqual(stats['by_status'].get('success', 0), 2)
        self.assertGreaterEqual(stats['by_status'].get('error', 0), 1)

if __name__ == '__main__':
    unittest.main()
