from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
import uuid
import os

class Clinician(AbstractUser):
    title = models.CharField(max_length=100, default='', help_text="Professional title (e.g., MD, Radiologist)")
    workplace = models.CharField(max_length=200, default='', help_text="Hospital or institution name")
    years_experience = models.PositiveIntegerField(default=0, help_text="Years of professional experience")

    def __str__(self):
        return self.username

class ImageSet(models.Model):
    """A collection of images loaded by an admin for evaluation"""
    name = models.CharField(max_length=255, unique=True, help_text="Unique name for this image set")
    description = models.TextField(blank=True, null=True, help_text="Optional description of this image set")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Clinician, on_delete=models.SET_NULL, null=True, related_name='created_imagesets')
    is_active = models.BooleanField(default=True, help_text="Whether this image set is available for evaluation")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.images.count()} images)"
    
    def get_real_count(self):
        return self.images.filter(is_real=True).count()
    
    def get_synth_count(self):
        return self.images.filter(is_real=False).count()

def get_upload_path(instance, filename):
    folder = 'real' if instance.is_real else 'synth'
    # Sanitize imageset name to be safe for filenames if needed
    return f"image_sets/{instance.image_set.name}/data/{folder}/{filename}"

class Image(models.Model):
    """Individual image within an image set"""
    image_set = models.ForeignKey(ImageSet, on_delete=models.CASCADE, related_name='images')
    file = models.ImageField(
        upload_to=get_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Image file"
    )
    original_filename = models.CharField(max_length=255, help_text="Original filename from upload")
    is_real = models.BooleanField(help_text="True if real image, False if synthetic")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['original_filename']
        unique_together = [['image_set', 'original_filename']]
    
    def __str__(self):
        return f"{self.image_set.name} - {self.original_filename}"
    
    def get_image_path(self):
        """Returns the relative path for backwards compatibility"""
        return self.file.name

class Assignment(models.Model):
    """Assignment of an image set to a clinician for evaluation"""
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE, related_name='assignments')
    image_set = models.ForeignKey(ImageSet, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(Clinician, on_delete=models.SET_NULL, null=True, related_name='assignments_created')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    assigned_images = models.ManyToManyField(Image, blank=True, related_name='assignments_subset', help_text="Specific subset of images assigned to this clinician. If empty, implies all images.")
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = [['clinician', 'image_set']]
    
    def __str__(self):
        return f"{self.clinician.username} - {self.image_set.name}"
    
    def get_progress(self):
        """Returns the evaluation progress as a percentage"""
        if self.pk and self.assigned_images.exists():
            total_images = self.assigned_images.count()
            evaluated_count = Evaluation.objects.filter(
                clinician=self.clinician,
                image__in=self.assigned_images.all()
            ).count()
        else:
            total_images = self.image_set.images.count()
            evaluated_count = Evaluation.objects.filter(
                clinician=self.clinician,
                image__image_set=self.image_set
            ).count()
            
        if total_images == 0:
            return 0
        return (evaluated_count / total_images) * 100
    
    def get_evaluated_count(self):
        """Returns the number of images evaluated"""
        if self.pk and self.assigned_images.exists():
            return Evaluation.objects.filter(
                clinician=self.clinician,
                image__in=self.assigned_images.all()
            ).count()
        return Evaluation.objects.filter(
            clinician=self.clinician,
            image__image_set=self.image_set
        ).count()

class Evaluation(models.Model):
    clinician = models.ForeignKey(Clinician, on_delete=models.CASCADE)
    image = models.ForeignKey('Image', on_delete=models.CASCADE, null=True, blank=True, related_name='evaluations')
    # Keep image_path for backwards compatibility with old evaluations
    image_path = models.CharField(max_length=255, blank=True, null=True)
    is_real = models.BooleanField(help_text="True if the user thinks it's real, False if synthetic")
    confidence = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], help_text="1-5 confidence score")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['clinician', 'image']]
    
    def __str__(self):
        if self.image:
            return f"{self.clinician.username} - {self.image.original_filename} - {self.confidence}"
        return f"{self.clinician.username} - {self.image_path} - {self.confidence}"

class Invitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.token)
