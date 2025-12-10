from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class Clinician(AbstractUser):
    title = models.CharField(max_length=100, blank=True, null=True)
    years_experience = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username

class Evaluation(models.Model):
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE)
    image_path = models.CharField(max_length=255)
    is_real = models.BooleanField(help_text="True if the user thinks it's real, False if synthetic")
    confidence = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], help_text="1-5 confidence score")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.clinician.username} - {self.image_path} - {self.confidence}"

class Invitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.token)
