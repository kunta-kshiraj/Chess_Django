from django.db import models

# Create your models here.
from django.contrib.auth.models import User


class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='general_journal_entries')  # Use a different related name
    datetime = models.DateField(auto_now=True)
    description = models.CharField(max_length=128)
    entry = models.CharField(max_length=65536)

    def __str__(self):
        return f"Journal entry by {self.user.username}"