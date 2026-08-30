from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """
    Extra fields for a customer, layered on top of Django's built-in User.
    Staff/admin distinctions use Django's built-in is_staff / is_superuser
    flags rather than a custom role field, so the built-in Django admin
    site's permission system works correctly out of the box.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=30, blank=True)
    delivery_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"
