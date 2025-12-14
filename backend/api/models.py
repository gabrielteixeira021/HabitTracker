from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    name = models.CharField(max_length=200)
    frequency = models.CharField(
        choices=FREQUENCY_CHOICES,
        max_length=10,
    )
    current_streak = models.IntegerField(default=0)  # pyright: ignore[reportArgumentType]
    best_streak = models.IntegerField(default=0)  # pyright: ignore[reportArgumentType]
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")


def __str__(self):
    return self.name
