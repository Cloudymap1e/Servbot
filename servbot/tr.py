import imapclient


imap_server = "imap.shanyouxiang.com"

imap_port = 993
username = "sdeyqkhu2105@outlook.com"
password = "mhlod7WM1"

ssh_password = "Nowk9y7u7d"

imap_obj = imapclient.IMAPClient(imap_server, use_uid=True, port=imap_port, ssl=True)
imap_obj.login(username, password)
imap_obj.select_folder("INBOX")

def fetch_emails():
    UIDs = imap_obj.search(['ALL'])
    emails = imap_obj.fetch(UIDs, ['BODY[]', 'FLAGS'])
    return emails

if __name__ == "__main__":
    emails = fetch_emails()
    for uid, message in emails.items():
        print(f"Email UID: {uid}")
        print(message['BODY[]'])

