from django.db import models


class Table(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("reserved", "Reserved"),
    ]

    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Table {self.number} (seats {self.capacity})"
