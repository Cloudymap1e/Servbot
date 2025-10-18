import unittest
from pathlib import Path
import os
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servbot.data import database as db

# Define a path for the test database file
TEST_DB_PATH = Path(__file__).parent / "test_servbot.db"

class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Set up a clean test database before each test."""
        # Override the default DB_PATH in the db module
        db.DB_PATH = TEST_DB_PATH
        # Initialize the database schema
        db.init_db()

    def tearDown(self):
        """Remove the test database file after each test."""
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_01_init_db(self):
        conn = db._connect()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
        self.assertIn("accounts", tables)
        self.assertIn("messages", tables)
        self.assertIn("verifications", tables)
        self.assertIn("graph_accounts", tables)

    def test_02_upsert_account(self):
        acc_id = db.upsert_account(email="test@example.com", password="password", source="test")
        self.assertGreater(acc_id, 0)
        
        accounts = db.get_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]['email'], "test@example.com")

        db.upsert_account(email="test@example.com", password="new_password")
        accounts = db.get_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]['password'], "new_password")

    def test_03_save_message_and_verification(self):
        msg_id = db.save_message(
            mailbox="test@example.com", provider="imap", provider_msg_id="123",
            subject="Code", body_text="12345", service="TestSvc"
        )
        self.assertGreater(msg_id, 0)

        ver_id = db.save_verification(message_id=msg_id, service="TestSvc", value="12345", is_link=False)
        self.assertGreater(ver_id, 0)

        verifs = db.get_latest_verifications(mailbox="test@example.com")
        self.assertEqual(len(verifs), 1)
        self.assertEqual(verifs[0]['value'], "12345")

    def test_04_graph_account(self):
        self.assertIsNone(db.get_graph_account())
        db.upsert_graph_account(email="graph@example.com", refresh_token="abc", client_id="123")
        acct = db.get_graph_account()
        self.assertIsNotNone(acct)
        self.assertEqual(acct['email'], "graph@example.com")

    def test_05_find_verification(self):
        msg_id = db.save_message(mailbox="find@test.com", provider="test", provider_msg_id="1")
        db.save_verification(message_id=msg_id, service="MyService", value="111222", is_link=False)

        found = db.find_verification(service="MyService", mailbox="find@test.com")
        self.assertIsNotNone(found)
        self.assertEqual(found['value'], "111222")
        self.assertIsNone(db.find_verification(service="OtherService"))

    def test_06_migrate_email_txt(self):
        # Temporarily create a dummy email.txt
        dummy_path = db.DATA_DIR / "email.txt"
        db.DATA_DIR.mkdir(exist_ok=True)
        original_content = dummy_path.read_text() if dummy_path.exists() else None
        
        try:
            dummy_path.write_text("migrated1@example.com----pass1\n")
            db.migrate_email_txt_to_db()
            accounts = db.get_accounts(source="file")
            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts[0]['email'], "migrated1@example.com")
        finally:
            # Restore original state
            if original_content is not None:
                dummy_path.write_text(original_content)
            elif dummy_path.exists():
                os.remove(dummy_path)

if __name__ == "__main__":
    unittest.main()