from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()


class AuthenticationTests(TestCase):
    def test_register_creates_user_profile_and_logs_in(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newcook", "email": "New@Example.com", "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = User.objects.get(username="newcook")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password("Sup3r-secret-pw"))
        self.assertNotEqual(user.password, "Sup3r-secret-pw")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_rejects_duplicate_email_and_mismatched_passwords(self):
        User.objects.create_user("existing", "dup@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:register"), {
            "username": "other", "email": "dup@example.com", "password1": "Sup3r-secret-pw", "password2": "Sup3r-secret-pw"})
        self.assertContains(response, "already exists")
        response = self.client.post(reverse("accounts:register"), {
            "username": "other", "email": "o@example.com", "password1": "Sup3r-secret-pw", "password2": "different"})
        self.assertFalse(User.objects.filter(username="other").exists())
        self.assertEqual(response.status_code, 200)

    def test_login_and_logout(self):
        User.objects.create_user("alice", "a@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "pass12345!"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        User.objects.create_user("alice", "a@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_and_profile_require_login(self):
        for name in ("accounts:dashboard", "accounts:profile"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login/", response["Location"])

    def test_profile_update(self):
        user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        self.client.force_login(user)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Alice", "last_name": "Baker", "email": "alice@example.com", "default_servings": 2})
        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Alice")
        self.assertEqual(user.profile.default_servings, 2)

    def test_password_reset_sends_email(self):
        User.objects.create_user("alice", "a@example.com", "pass12345!")
        response = self.client.post(reverse("accounts:password_reset"), {"email": "a@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/password-reset/confirm/", mail.outbox[0].body)
