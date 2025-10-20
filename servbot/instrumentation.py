from __future__ import annotations

try:
    from . import event_logger as elog
except Exception:
    elog = None  # type: ignore

def _safe_log(event_type: str, status: str = 'info', **details):
    if elog is None:
        return
    try:
        service = details.pop('service', 'app')
        elog.log_event(event_type, status, service=service, details=details)
    except Exception:
        pass

def _patch_database():
    try:
        from .data import database as db
    except Exception:
        return

    # upsert_account
    orig_upsert = db.upsert_account
    def upsert_wrapper(*args, **kwargs):
        email = kwargs.get('email') if isinstance(kwargs, dict) else None
        source = kwargs.get('source') if isinstance(kwargs, dict) else None
        acc_type = kwargs.get('type') if isinstance(kwargs, dict) else None
        try:
            acc_id = orig_upsert(*args, **kwargs)
            if email:
                if not acc_type:
                    try:
                        acc_type_local = db.infer_type_from_email(email)
                    except Exception:
                        acc_type_local = None
                else:
                    acc_type_local = acc_type
                _safe_log('account_upsert', 'success', service='db', email=email, source=source or '', type=acc_type_local, account_id=acc_id)
            return acc_id
        except Exception as e:
            if email:
                _safe_log('account_upsert', 'error', service='db', email=email, source=source or '', error=str(e))
            raise
    db.upsert_account = upsert_wrapper

    # save_message
    orig_save_msg = db.save_message
    def save_message_wrapper(*args, **kwargs):
        try:
            mid = orig_save_msg(*args, **kwargs)
            mailbox = kwargs.get('mailbox')
            provider = kwargs.get('provider')
            provider_msg_id = kwargs.get('provider_msg_id')
            if mailbox and provider and provider_msg_id:
                _safe_log('message_save', 'success', service=str(provider), mailbox=str(mailbox), provider_msg_id=str(provider_msg_id), message_id=mid)
            return mid
        except Exception as e:
            mailbox = kwargs.get('mailbox')
            provider = kwargs.get('provider')
            _safe_log('message_save', 'error', service=str(provider or 'mail'), mailbox=str(mailbox or ''), error=str(e))
            raise
    db.save_message = save_message_wrapper

    # save_verification
    orig_save_ver = db.save_verification
    def save_verification_wrapper(*args, **kwargs):
        try:
            vid = orig_save_ver(*args, **kwargs)
            svc = kwargs.get('service')
            message_id = kwargs.get('message_id')
            value = kwargs.get('value')
            is_link = bool(kwargs.get('is_link'))
            _safe_log('verification_extract', 'success', service=str(svc or 'parser'), message_id=int(message_id or 0), value=str(value or ''), is_link=is_link, verification_id=vid)
            return vid
        except Exception as e:
            svc = kwargs.get('service')
            _safe_log('verification_extract', 'error', service=str(svc or 'parser'), error=str(e))
            raise
    db.save_verification = save_verification_wrapper

    # save_registration
    orig_save_reg = db.save_registration
    def save_registration_wrapper(*args, **kwargs):
        try:
            rid = orig_save_reg(*args, **kwargs)
            svc = kwargs.get('service')
            mailbox = kwargs.get('mailbox_email')
            status = kwargs.get('status', 'success')
            _safe_log('registration', str(status or 'success'), service=str(svc or 'automation'), mailbox=str(mailbox or ''), registration_id=rid)
            return rid
        except Exception as e:
            svc = kwargs.get('service')
            mailbox = kwargs.get('mailbox_email')
            _safe_log('registration', 'error', service=str(svc or 'automation'), mailbox=str(mailbox or ''), error=str(e))
            raise
    db.save_registration = save_registration_wrapper

    # update_registration_status
    orig_update_reg = db.update_registration_status
    def update_registration_status_wrapper(*args, **kwargs):
        try:
            ok = orig_update_reg(*args, **kwargs)
            reg_id = kwargs.get('registration_id')
            status = kwargs.get('status')
            _safe_log('registration_update', str(status or ''), service='automation', registration_id=int(reg_id or 0), ok=bool(ok), error=str(kwargs.get('error') or ''))
            return ok
        except Exception as e:
            _safe_log('registration_update', 'error', service='automation', error=str(e))
            raise
    db.update_registration_status = update_registration_status_wrapper

def _patch_graph_client():
    try:
        from .clients.graph import GraphClient
    except Exception:
        return
    orig_fetch = GraphClient.fetch_messages
    def fetch_messages_wrapper(self, *args, **kwargs):
        try:
            msgs = orig_fetch(self, *args, **kwargs)
            try:
                count = len(msgs) if hasattr(msgs, '__len__') else 0
            except Exception:
                count = 0
            _safe_log('email_fetch', 'success', service='graph', mailbox=getattr(self, 'mailbox', ''), fetched=count)
            return msgs
        except Exception as e:
            _safe_log('email_fetch', 'error', service='graph', mailbox=getattr(self, 'mailbox', ''), error=str(e))
            raise
    GraphClient.fetch_messages = fetch_messages_wrapper

# Apply patches on import
_patch_database()
_patch_graph_client()

def _patch_api():
    try:
        from . import api
    except Exception:
        return
    if hasattr(api, 'provision_flashmail_account'):
        orig = api.provision_flashmail_account
        def provision_wrapper(*args, **kwargs):
            try:
                result = orig(*args, **kwargs)
                try:
                    email = (result or {}).get('email') if isinstance(result, dict) else None
                except Exception:
                    email = None
                _safe_log('account_provision', 'success', service='flashmail', email=str(email or ''))
                return result
            except Exception as e:
                _safe_log('account_provision', 'error', service='flashmail', error=str(e))
                raise
        api.provision_flashmail_account = provision_wrapper
_patch_api()
