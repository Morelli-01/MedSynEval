from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.conf import settings
from .models import Clinician, Evaluation, Invitation, ImageSet, Image, Assignment
import json
import logging

logger = logging.getLogger(__name__)


def send_assignment_notification(assignment, assigned_by):
    """
    Send an email notification to the clinician about their new assignment.
    The email is sent using the superuser's (assigned_by) email address.
    """
    clinician = assignment.clinician
    image_set = assignment.image_set
    
    # Check if clinician has a valid email
    if not clinician.email:
        logger.warning(f"Cannot send assignment notification: Clinician {clinician.username} has no email address")
        return False
    
    # Check if assigned_by user has an email (to use as sender)
    sender_email = assigned_by.email if assigned_by and assigned_by.email else settings.DEFAULT_FROM_EMAIL
    
    subject = f"New Image Evaluation Assignment: {image_set.name}"
    
    # Count assigned images
    if assignment.pk and assignment.assigned_images.exists():
        image_count = assignment.assigned_images.count()
    else:
        image_count = image_set.images.count()
    
    # Application URL
    app_url = "https://zip-dgx.ing.unimore.it/"
    
    message = f"""
Dear {clinician.first_name or clinician.username},

You have been assigned a new image evaluation task.

Assignment Details:
- Image Set: {image_set.name}
- Number of Images: {image_count}
- Assigned By: {assigned_by.get_full_name() or assigned_by.username if assigned_by else 'System'}

Please log in to MedSynEval to start your evaluation:
{app_url}

Best regards,
AImageLab Team
"""
    
    html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c5282;">New Image Evaluation Assignment</h2>
        
        <p>Dear <strong>{clinician.first_name or clinician.username}</strong>,</p>
        
        <p>You have been assigned a new image evaluation task.</p>
        
        <div style="background-color: #f7fafc; border-left: 4px solid #4299e1; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2b6cb0;">Assignment Details</h3>
            <ul style="list-style: none; padding: 0; margin: 0;">
                <li><strong>Image Set:</strong> {image_set.name}</li>
                <li><strong>Number of Images:</strong> {image_count}</li>
                <li><strong>Assigned By:</strong> {assigned_by.get_full_name() or assigned_by.username if assigned_by else 'System'}</li>
            </ul>
        </div>
        
        <p>Please log in to <strong>MedSynEval</strong> to start your evaluation:</p>
        
        <p style="text-align: center; margin: 25px 0;">
            <a href="{app_url}" style="display: inline-block; background-color: #4299e1; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Start Evaluation</a>
        </p>
        
        <p style="color: #718096; font-size: 12px;">Or copy and paste this link in your browser:<br><a href="{app_url}" style="color: #4299e1;">{app_url}</a></p>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
        
        <p style="color: #718096; font-size: 12px;">Best regards,<br>AImageLab Team</p>
    </div>
</body>
</html>
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=sender_email,
            recipient_list=[clinician.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Assignment notification sent to {clinician.email} from {sender_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send assignment notification to {clinician.email}: {str(e)}")
        return False


class ClinicianAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'title', 'workplace','years_experience', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Professional Info', {'fields': ('title', 'workplace', 'years_experience')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Professional Info', {'fields': ('title', 'workplace', 'years_experience')}),
    )

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'get_image_display', 'is_real', 'confidence', 'timestamp', 'is_correct_display')
    list_filter = ('is_real', 'confidence', 'timestamp')
    search_fields = ('clinician__username', 'image__original_filename')
    readonly_fields = ('timestamp',)
    actions = ['export_as_json']

    def get_image_display(self, obj):
        if obj.image:
            return obj.image.original_filename
        return obj.image_path
    get_image_display.short_description = "Image"

    def is_correct_display(self, obj):
        if obj.image:
            return obj.is_real == obj.image.is_real
        return "-"
    is_correct_display.short_description = "Correct?"
    is_correct_display.boolean = True
    
    def export_as_json(self, request, queryset):
        """Export selected evaluations as JSON file"""
        evaluations_data = []
        
        for evaluation in queryset:
            evaluations_data.append({
                'id': evaluation.id,
                'clinician': {
                    'username': evaluation.clinician.username,
                    'email': evaluation.clinician.email,
                    'first_name': evaluation.clinician.first_name,
                    'last_name': evaluation.clinician.last_name,
                    'title': evaluation.clinician.title,
                    'years_experience': evaluation.clinician.years_experience,
                },
                'image_set': evaluation.image.image_set.name,
                'image_path': evaluation.image.file.name,
                'original_filename': evaluation.image.original_filename,
                'ground_truth': evaluation.image.is_real,
                'user_prediction': evaluation.is_real,
                'is_correct': evaluation.is_real == evaluation.image.is_real,
                'confidence': evaluation.confidence,
                'timestamp': evaluation.timestamp.isoformat(),
            })
        
        # Create JSON response
        response = JsonResponse(evaluations_data, safe=False, json_dumps_params={'indent': 2})
        
        # Set filename with timestamp
        filename = f"evaluations_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    export_as_json.short_description = "Export selected evaluations as JSON"

admin.site.register(Clinician, ClinicianAdmin)

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('token', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    readonly_fields = ('token',)


# ImageSet Admin
class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    readonly_fields = ('original_filename', 'is_real', 'uploaded_at', 'image_preview')
    fields = ('image_preview', 'original_filename', 'is_real', 'uploaded_at')
    can_delete = True
    
    def image_preview(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.file.url)
        return "-"
    image_preview.short_description = "Preview"


@admin.register(ImageSet)
class ImageSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_count', 'real_count', 'synth_count', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'created_by', 'image_count', 'real_count', 'synth_count')
    inlines = [ImageInline]
    actions = ['assign_split_action']
    change_list_template = 'admin/imageset_changelist.html'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Statistics', {
            'fields': ('image_count', 'real_count', 'synth_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = "Total Images"
    
    def real_count(self, obj):
        return obj.get_real_count()
    real_count.short_description = "Real Images"
    
    def synth_count(self, obj):
        return obj.get_synth_count()
    synth_count.short_description = "Synthetic Images"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('load-from-folder/', self.admin_site.admin_view(self.load_from_folder_view), name='imageset_load_from_folder'),
        ]
        return custom_urls + urls
    
    def load_from_folder_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from pathlib import Path
        import os
        import zipfile
        import tempfile
        import shutil
        from django.core.files import File
        
        if request.method == 'POST':
            zip_file = request.FILES.get('zip_file')
            imageset_name = request.POST.get('imageset_name')
            description = request.POST.get('description', '')
            
            if not zip_file:
                messages.error(request, "Please upload a ZIP file")
                return render(request, 'admin/load_imageset_form.html')

            # Check if ImageSet already exists
            if ImageSet.objects.filter(name=imageset_name).exists():
                messages.error(request, f"ImageSet with name '{imageset_name}' already exists")
                return render(request, 'admin/load_imageset_form.html')
            
            try:
                # Create temp directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # Save uploaded zip
                    zip_path = temp_path / 'upload.zip'
                    with open(zip_path, 'wb+') as destination:
                        for chunk in zip_file.chunks():
                            destination.write(chunk)
                    
                    # Extract zip
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_path)
                    except zipfile.BadZipFile:
                         messages.error(request, "Invalid ZIP file")
                         return render(request, 'admin/load_imageset_form.html')
                    
                    # Locate real and synth folders
                    # Possible structures:
                    # 1. Root -> real/, synth/
                    # 2. Root -> Folder/ -> real/, synth/
                    
                    real_folder = None
                    synth_folder = None
                    
                    # Check root
                    if (temp_path / 'real').exists() and (temp_path / 'synth').exists():
                        real_folder = temp_path / 'real'
                        synth_folder = temp_path / 'synth'
                    else:
                        # Check subdirectories
                        for child in temp_path.iterdir():
                            if child.is_dir():
                                if (child / 'real').exists() and (child / 'synth').exists():
                                    real_folder = child / 'real'
                                    synth_folder = child / 'synth'
                                    break
                    
                    if not real_folder or not synth_folder:
                        messages.error(request, "Could not find 'real' and 'synth' folders in the ZIP file. Please ensure the structure is correct.")
                        return render(request, 'admin/load_imageset_form.html')
                    
                    # Create ImageSet
                    image_set = ImageSet.objects.create(
                        name=imageset_name,
                        description=description,
                        created_by=request.user
                    )
                    
                    # Load images
                    allowed_extensions = {'.jpg', '.jpeg', '.png'}
                    total_loaded = 0
                    real_count = 0
                    synth_count = 0
                    
                    def process_folder(folder, is_real):
                        count = 0
                        for img_file in folder.iterdir():
                            if img_file.is_file() and img_file.suffix.lower() in allowed_extensions:
                                # Avoid dotfiles (like .DS_Store or ._image.jpg)
                                if img_file.name.startswith('.'):
                                    continue
                                    
                                with open(img_file, 'rb') as f:
                                    image = Image(
                                        image_set=image_set,
                                        original_filename=img_file.name,
                                        is_real=is_real
                                    )
                                    image.file.save(img_file.name, File(f), save=True)
                                    
                                    # Ensure file is world-readable (0o644) so web server can serve it
                                    try:
                                        full_path = image.file.path
                                        os.chmod(full_path, 0o644)
                                        # Ensure directory is executable/readable (0o755)
                                        os.chmod(os.path.dirname(full_path), 0o755)
                                    except Exception:
                                        pass # Best effort if permissions fail
                                        
                                    count += 1
                        return count

                    real_count = process_folder(real_folder, True)
                    synth_count = process_folder(synth_folder, False)
                    total_loaded = real_count + synth_count

                    if total_loaded == 0:
                         image_set.delete()
                         messages.error(request, "No valid images found in the 'real' and 'synth' folders.")
                         return render(request, 'admin/load_imageset_form.html')
                    
                messages.success(request, f"Successfully created ImageSet '{imageset_name}' with {total_loaded} images ({real_count} real, {synth_count} synthetic).")
                return redirect('admin:evaluator_imageset_changelist')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                # If image_set was created but failed mid-way, maybe delete it? 
                # For safety let's leave unless we are sure. But good practice is atomic.
                # Here we are in a try block.
                return render(request, 'admin/load_imageset_form.html')
        
        return render(request, 'admin/load_imageset_form.html')

    def assign_split_action(self, request, queryset):
        from django.shortcuts import render
        from django.contrib import admin
        import random
        
        if 'post' in request.POST:
            clinician_ids = request.POST.getlist('clinicians')
            if not clinician_ids:
                self.message_user(request, "No clinicians selected.", level='error')
                return None
            
            clinicians = list(Clinician.objects.filter(id__in=clinician_ids))
            num_clinicians = len(clinicians)
            
            if num_clinicians == 0:
                 self.message_user(request, "Selected clinicians not found.", level='error')
                 return None

            success_count = 0
            email_sent_count = 0
            email_failed_count = 0
            
            for imageset in queryset:
                images = list(imageset.images.all())
                if not images:
                    continue
                    
                random.shuffle(images)
                
                # Standard even split algorithm
                k, m = divmod(len(images), num_clinicians)
                chunks = [images[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(num_clinicians)]
                
                # Assign to each clinician
                for i, clinician in enumerate(clinicians):
                    if i < len(chunks):
                        images_subset = chunks[i]
                        # Create or get assignment
                        assignment, created = Assignment.objects.get_or_create(
                            clinician=clinician,
                            image_set=imageset,
                            defaults={'assigned_by': request.user}
                        )
                        # Set the specific subset of images
                        assignment.assigned_images.set(images_subset)
                        # Reset completion status if re-assigning? 
                        # For safety, let's untick completed if we are giving new images.
                        assignment.is_completed = False
                        assignment.save()
                        
                        # Send email notification
                        if send_assignment_notification(assignment, request.user):
                            email_sent_count += 1
                        else:
                            email_failed_count += 1
                            
                success_count += 1
            
            # Build feedback message
            message = f"Successfully split and assigned {success_count} ImageSets to {num_clinicians} clinicians."
            if email_sent_count > 0:
                message += f" {email_sent_count} email notification(s) sent."
            if email_failed_count > 0:
                message += f" {email_failed_count} email(s) failed to send."
            
            self.message_user(request, message)
            return None

        # Render selection form
        context = {
            'clinicians': Clinician.objects.filter(is_active=True),
            'imageset': queryset.first() if queryset.count() == 1 else None,
            'queryset': queryset,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }
        return render(request, 'admin/assign_split_form.html', context)
    
    assign_split_action.short_description = "Assign to multiple users (Split)"


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'image_set', 'is_real', 'uploaded_at', 'image_preview')
    list_filter = ('is_real', 'image_set', 'uploaded_at')
    search_fields = ('original_filename', 'image_set__name')
    readonly_fields = ('uploaded_at', 'image_preview_large')
    
    fieldsets = (
        ('Image Information', {
            'fields': ('image_set', 'file', 'original_filename', 'is_real')
        }),
        ('Preview', {
            'fields': ('image_preview_large',)
        }),
        ('Metadata', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.file.url)
        return "-"
    image_preview.short_description = "Preview"
    
    def image_preview_large(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-height: 400px; max-width: 600px;" />', obj.file.url)
        return "-"
    image_preview_large.short_description = "Image Preview"


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'image_set', 'progress_display', 'is_completed', 'assigned_at', 'assigned_by')
    list_filter = ('is_completed', 'assigned_at', 'image_set')
    search_fields = ('clinician__username', 'image_set__name')
    readonly_fields = ('assigned_at', 'assigned_by', 'progress_display', 'evaluated_count', 'total_images')
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('clinician', 'image_set')
        }),
        ('Progress', {
            'fields': ('progress_display', 'evaluated_count', 'total_images', 'is_completed', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('assigned_at', 'assigned_by'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        progress = obj.get_progress()
        color = 'green' if progress == 100 else 'orange' if progress > 50 else 'red'
        progress_text = f'{progress:.1f}%'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; line-height: 20px;">'
            '{}'
            '</div></div>',
            progress, color, progress_text
        )
    progress_display.short_description = "Progress"
    
    def evaluated_count(self, obj):
        return obj.get_evaluated_count()
    evaluated_count.short_description = "Evaluated"
    
    def total_images(self, obj):
        return obj.image_set.images.count()
    total_images.short_description = "Total Images"
    save_on_top = True

    def save_model(self, request, obj, form, change):
        is_new_assignment = not change
        
        if is_new_assignment:  # Only set assigned_by on creation
            obj.assigned_by = request.user
        
        # Check if assignment is completed
        if obj.get_progress() == 100 and not obj.is_completed:
            obj.is_completed = True
            obj.completed_at = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Send email notification for new assignments
        if is_new_assignment:
            send_assignment_notification(obj, request.user)

