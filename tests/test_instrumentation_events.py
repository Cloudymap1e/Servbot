import unittest
from pathlib import Path
import sys

sys.path.insert(0, '/root/servbot')

import servbot  # triggers auto-instrumentation
from servbot.data import database as db
from servbot import event_logger as elog

TEST_DB_PATH = Path(__file__).parent / 'test_instrumentation.db'

class TestInstrumentationEvents(unittest.TestCase):
    def setUp(self):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
        db.DB_PATH = TEST_DB_PATH
        db.init_db()

    def tearDown(self):
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()

    def test_wraps_emit_events(self):
        acc_id = db.upsert_account(email='inst_wrap@example.com', password='pw', source='test')
        self.assertGreater(acc_id, 0)

        msg_id = db.save_message(mailbox='inst_wrap@example.com', provider='imap', provider_msg_id='xx1')
        self.assertGreater(msg_id, 0)

        ver_id = db.save_verification(message_id=msg_id, service='TestSvc', value='111222', is_link=False)
        self.assertGreater(ver_id, 0)

        reg_id = db.save_registration(service='Svc', mailbox_email='inst_wrap@example.com')
        self.assertGreater(reg_id, 0)

        ok = db.update_registration_status(registration_id=reg_id, status='done')
        self.assertTrue(ok)

        evs = elog.get_recent_events(20)
        kinds = {e['event_type'] for e in evs}
        self.assertTrue({'account_upsert','message_save','verification_extract','registration','registration_update'} <= kinds)

        stats = elog.get_event_stats()
        self.assertGreaterEqual(stats['by_type'].get('account_upsert', 0), 1)
        self.assertGreaterEqual(stats['by_type'].get('message_save', 0), 1)
        self.assertGreaterEqual(stats['by_type'].get('verification_extract', 0), 1)
        self.assertGreaterEqual(stats['by_type'].get('registration', 0), 1)
        self.assertGreaterEqual(stats['by_type'].get('registration_update', 0), 1)

if __name__ == '__main__':
    unittest.main()
