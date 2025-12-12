from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import Clinician, Evaluation, Invitation, ImageSet, Image, Assignment
import json

class ClinicianAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('title', 'years_experience')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('title', 'years_experience')}),
    )

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'image_path', 'is_real', 'confidence', 'timestamp')
    list_filter = ('is_real', 'confidence', 'timestamp')
    search_fields = ('clinician__username', 'image_path')
    readonly_fields = ('timestamp',)
    actions = ['export_as_json']
    
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
                'image_path': evaluation.image_path,
                'is_real': evaluation.is_real,
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
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set assigned_by on creation
            obj.assigned_by = request.user
        
        # Check if assignment is completed
        if obj.get_progress() == 100 and not obj.is_completed:
            obj.is_completed = True
            obj.completed_at = timezone.now()
        
        super().save_model(request, obj, form, change)

