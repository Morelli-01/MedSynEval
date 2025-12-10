from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import JsonResponse
from django.utils import timezone
from .models import Clinician, Evaluation, Invitation
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
