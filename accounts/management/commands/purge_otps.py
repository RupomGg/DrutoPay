from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import OTP


class Command(BaseCommand):
    help = "Delete expired OTP rows. Run periodically (cron / scheduled task)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        expired = OTP.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} expired OTP row(s) would be deleted.")
            return

        deleted, _ = expired.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} expired OTP row(s)."))
