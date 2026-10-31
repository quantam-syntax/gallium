from datetime import timedelta
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from yascn.models import User
from yascn.password_reset import _connection


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("owner@example.com", "OldPassword!", full_name="Owner")

    def setUp(self):
        cache.clear()

    def request_reset(self, email="OWNER@example.com"):
        return self.client.post("/api/auth/password-reset/request", {"email": email}, format="json")

    def link_data(self):
        response = self.request_reset()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(mail.outbox), 1)
        url = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http"))
        values = parse_qs(urlparse(url).query)
        return {"uid": values["uid"][0], "token": values["token"][0], "password": "NewPassword!"}

    def confirm(self, data):
        return self.client.post("/api/auth/password-reset/confirm", data, format="json")

    def test_captured_email_reset_revokes_existing_tokens_and_is_single_use(self):
        old_token = Token.objects.create(user=self.user).key
        data = self.link_data()
        self.assertEqual(self.confirm(data).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword!"))
        self.assertFalse(self.user.check_password("OldPassword!"))
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertEqual(self.confirm(data).status_code, 400)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + old_token)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post("/api/auth/login", {"email": self.user.email, "password": "NewPassword!"}).status_code, 200)

    def test_unknown_and_inactive_accounts_have_same_response_and_no_mail(self):
        known = self.request_reset()
        mail.outbox.clear()
        absent = self.request_reset("absent@example.com")
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        inactive = self.request_reset()
        self.assertEqual(known.data, absent.data)
        self.assertEqual(known.data, inactive.data)
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn("token", known.data)
        self.assertNotIn("uid", known.data)

    def test_malformed_uid_tampered_token_and_wrong_account_are_rejected(self):
        data = self.link_data()
        other = User.objects.create_user("other@example.com", "OtherPassword!", full_name="Other")
        for bad in [{**data, "uid": "!"}, {**data, "token": "wrong"},
                    {**data, "uid": urlsafe_base64_encode(force_bytes(other.pk))},
                    {**data, "uid": urlsafe_base64_encode(force_bytes(2**100))}]:
            response = self.confirm(bad)
            self.assertEqual(response.status_code, 400, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword!"))

    @override_settings(PASSWORD_RESET_TIMEOUT=60)
    def test_expired_token_is_rejected(self):
        data = self.link_data()
        later = default_token_generator._now() + timedelta(seconds=61)
        with patch.object(default_token_generator, "_now", return_value=later):
            self.assertEqual(self.confirm(data).status_code, 400)

    def test_weak_password_does_not_consume_reset_token(self):
        data = self.link_data()
        for password in ["short!Aa", "alllowercase!", "ALLUPPERCASE!", "NoSpecial123"]:
            response = self.confirm({**data, "password": password})
            self.assertEqual(response.status_code, 400)
            self.assertIn("password", response.data)
        self.assertEqual(self.confirm(data).status_code, 200)

    def test_deactivated_account_cannot_confirm_existing_link(self):
        data = self.link_data()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.confirm(data).status_code, 400)

    def test_delivery_failure_does_not_leak_account_or_token(self):
        with patch("yascn.password_reset.send_mail", side_effect=OSError("offline")):
            with self.assertLogs("yascn.password_reset", level="WARNING") as logs:
                response = self.request_reset()
        unknown = self.request_reset("absent@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, unknown.data)
        self.assertNotIn(self.user.email, " ".join(logs.output))

    def test_request_throttling(self):
        for _ in range(5):
            self.assertEqual(self.request_reset("absent@example.com").status_code, 200)
        self.assertEqual(self.request_reset("absent@example.com").status_code, 429)

    def test_configured_frontend_link_and_smtp_transport(self):
        with patch.dict("os.environ", {"BRIGHTLOOP_PASSWORD_RESET_URL": "https://example.test/reset?source=mail"}):
            self.link_data()
        self.assertIn("https://example.test/reset?source=mail&uid=", mail.outbox[0].body)
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"):
            with patch.dict("os.environ", {"BRIGHTLOOP_SMTP_HOST": "smtp.example.test", "BRIGHTLOOP_SMTP_PORT": "587",
                    "BRIGHTLOOP_SMTP_USER": "mailer", "BRIGHTLOOP_SMTP_PASSWORD": "secret", "BRIGHTLOOP_SMTP_TLS": "true"}):
                connection = _connection()
                self.assertEqual(connection.host, "smtp.example.test")
                self.assertEqual(connection.port, 587)
                self.assertTrue(connection.use_tls)
                self.assertEqual(connection.username, "mailer")

    def test_file_backend_captures_reset_email_locally(self):
        with TemporaryDirectory(prefix="yascn-mail-") as folder:
            with override_settings(EMAIL_BACKEND="django.core.mail.backends.filebased.EmailBackend", EMAIL_FILE_PATH=folder):
                self.assertEqual(self.request_reset().status_code, 200)
            messages = list(Path(folder).glob("*.log"))
            self.assertEqual(len(messages), 1)
            content = messages[0].read_text()
            self.assertIn("Reset your Brightloop password", content)
            self.assertIn("uid=", content)
            self.assertIn("token=", content)
