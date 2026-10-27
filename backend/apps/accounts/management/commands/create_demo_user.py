r"""
Creates (or resets) the demo account used for presentations.

    ..\.venv\Scripts\python manage.py create_demo_user

The email and password come from DEMO_USER_EMAIL / DEMO_USER_PASSWORD in
backend/.env, so no password is written in the code.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or reset the demo account from DEMO_USER_EMAIL and DEMO_USER_PASSWORD."

    def handle(self, *args, **options):
        email = os.environ.get("DEMO_USER_EMAIL", "").strip().lower()
        password = os.environ.get("DEMO_USER_PASSWORD", "")
        if not email or not password or password == "change-me":
            raise CommandError("Set DEMO_USER_EMAIL and DEMO_USER_PASSWORD in backend/.env first.")

        user, created = get_user_model().objects.get_or_create(
            username=email, defaults={"email": email, "first_name": "Demo Seller"}
        )
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Demo user {'created' if created else 'updated'}: {email}"))
