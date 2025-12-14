from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import RelatedManager


# Create your models here.
class Habit(models.Model):
    if TYPE_CHECKING:
        checkins: "RelatedManager[CheckIn]"
    
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    COLOR_CHOICES = [
        ("#3B82F6", "Azul"),
        ("#10B981", "Verde"),
        ("#F59E0B", "Amarelo"),
        ("#EF4444", "Vermelho"),
        ("#8B5CF6", "Roxo"),
        ("#EC4899", "Rosa"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")

    name = models.CharField(
        max_length=200, help_text="Nome do hábito (Ex: Fazer exercícios físicos)"
    )

    description = models.TextField(
        max_length=500, blank=True, help_text="Descrição do hábito"
    )

    frequency = models.CharField(
        choices=FREQUENCY_CHOICES, max_length=10, default="daily"
    )

    target_count = models.PositiveIntegerField(
        default=1,  # pyright: ignore[reportArgumentType]
        help_text="Quantidade de vezes que o hábito deve ser realizado",
    )

    color = models.CharField(
        max_length=7,
        choices=COLOR_CHOICES,
        default="#3B82F6",
        help_text="Cor do hábito",
    )

    is_active = models.BooleanField(default=True, help_text="Hábito ativo")  # pyright: ignore[reportArgumentType]

    current_streak = models.PositiveIntegerField(default=0)  # pyright: ignore[reportArgumentType]
    best_streak = models.PositiveIntegerField(default=0)  # pyright: ignore[reportArgumentType]
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_habit_name")
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def clean(self):
        """Custom Validation"""
        if self.frequency == "daily" and self.target_count > 7:
            raise ValidationError(
                "Para hábitos diários, o máximo é de 7 vezes por semana."
            )
        if self.frequency == "weekly" and self.target_count > 20:
            raise ValidationError(
                "Para hábitos semanais, o máximo é de 20 vezes por mês."
            )
        if self.frequency == "monthly" and self.target_count > 31:
            raise ValidationError(
                "Para hábitos mensais, o máximo é de 31 vezes por mês."
            )

    def success_rate(self) -> float:
        total_checkins = self.checkins.count()
        if total_checkins == 0:
            return 0.0
        return (self.checkins.filter(done=True).count() / total_checkins) * 100

    def get_streak_status(self) -> str:
        """Return the streak status of the habit"""

        if self.current_streak == 0:
            return "Comece seu streak!"
        elif self.current_streak == self.target_count:
            return "Você está no seu streak máximo!"
        else:
            return f"Você está em um streak de {self.current_streak} dias!"


class CheckIn(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField(
        default=timezone.now, help_text="Data em que o hábito foi realizado"
    )

    done = models.BooleanField(default=False)  # pyright: ignore[reportArgumentType]

    rating = models.PositiveSmallIntegerField(
        choices=[(i, f"{i}⭐") for i in range(1, 6)],
        null=True,
        blank=True,
        help_text="Avaliação de 1 a 5 estrelas para o check-in",
    )

    observations = models.TextField(
        max_length=1000, blank=True, help_text="Observações sobre o check-in"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "date"], name="unique_checkin_per_day"
            )
        ]
        ordering = ["-date"]
        verbose_name = "Check-in"
        verbose_name_plural = "Check-ins"

    def __str__(self):
        status = "🟢" if self.done else "🔴"
        return f"{self.habit.name} - {self.date} {status}"

    def clean(self):
        # Não permite check-ins em datas futuras
        if self.date > timezone.now().date():
            raise ValidationError(
                "Não é possível realizar um check-in em uma data futura."
            )
        # Não permite editar check-ins antigos (48hrs ou mais)
        if self.pk:
            original = CheckIn.objects.get(pk=self.pk)
            time_diff = timezone.now() - original.created_at
            if time_diff > timedelta(hours=48):
                raise ValidationError("Não é possível editar um check-in antigo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        # Atualiza streak apenas se for uma edição e mudou de False para True
        if self.done and self.pk:
            original = CheckIn.objects.get(pk=self.pk)
            if not original.done:
                self.update_streak()
        super().save(*args, **kwargs)

    def update_streak(self):
        habit = self.habit

        checkins = habit.checkins.filter(done=True).order_by("-date")

        if not checkins.exists():
            habit.current_streak = 0
        else:
            current_streak = 1
            dates = [c.date for c in checkins]

            for i in range(1, len(dates)):
                if (dates[i - 1] - dates[i]).days == 1:
                    current_streak += 1
                else:
                    break

            habit.current_streak = current_streak

        if habit.current_streak > habit.best_streak:
            habit.best_streak = habit.current_streak

        habit.save()
