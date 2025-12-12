from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Invitation, Evaluation, Assignment, Image, ImageSet
import uuid
import json

@require_http_methods(["POST"])
def validate_token(request):
    """API endpoint to validate invitation tokens"""
    try:
        data = json.loads(request.body)
        token_str = data.get('token', '').strip()
        
        if not token_str:
            return JsonResponse({'valid': False, 'message': 'Token is required'})
        
        # Validate UUID format first
        try:
            uuid.UUID(token_str)
        except (ValueError, AttributeError):
            return JsonResponse({'valid': False, 'message': 'Invalid or already used token'})
        
        try:
            invitation = Invitation.objects.get(token=token_str, is_used=False)
            return JsonResponse({'valid': True, 'message': 'Valid invitation token'})
        except Invitation.DoesNotExist:
            return JsonResponse({'valid': False, 'message': 'Invalid or already used token'})
            
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid request'}, status=400)

@require_http_methods(["POST"])
@login_required
def submit_evaluation(request):
    """API endpoint to submit an evaluation"""
    try:
        data = json.loads(request.body)
        image_id = data.get('image_id')
        is_real = data.get('is_real')
        confidence = data.get('confidence')
        
        # Validate inputs
        if not image_id or is_real is None or not confidence:
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
        
        # Get the image
        try:
            image = Image.objects.get(id=image_id)
        except Image.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid image'}, status=404)
        
        # Verify user has access to this image through assignments
        assignments = Assignment.objects.filter(
            clinician=request.user,
            image_set__is_active=True,
            is_completed=False
        )
        
        assigned_image_ids = []
        for assignment in assignments:
            assigned_image_ids.extend(
                assignment.image_set.images.values_list('id', flat=True)
            )
        
        if image.id not in assigned_image_ids:
            return JsonResponse({'success': False, 'message': 'Unauthorized access to this image'}, status=403)
        
        # Check if already evaluated
        if Evaluation.objects.filter(clinician=request.user, image=image).exists():
            return JsonResponse({'success': False, 'message': 'Image already evaluated'}, status=400)
        
        # Create evaluation
        evaluation = Evaluation.objects.create(
            clinician=request.user,
            image=image,
            is_real=is_real,
            confidence=int(confidence)
        )
        
        # Check if any assignments are now complete
        for assignment in assignments:
            if assignment.get_progress() == 100 and not assignment.is_completed:
                assignment.is_completed = True
                assignment.completed_at = timezone.now()
                assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Evaluation submitted successfully',
            'evaluation_id': evaluation.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@require_http_methods(["GET"])
@login_required
def get_next_image(request):
    """API endpoint to get the next unevaluated image"""
    try:
        # Get all active assignments for this clinician
        assignments = Assignment.objects.filter(
            clinician=request.user,
            image_set__is_active=True,
            is_completed=False
        ).select_related('image_set')
        
        # Filter by specific assignment if requested
        assignment_id = request.GET.get('assignment_id')
        if assignment_id:
            assignments = assignments.filter(id=assignment_id)
        
        if not assignments.exists():
            return JsonResponse({
                'success': True,
                'completed': True,
                'message': 'No active assignments'
            })
        
        # Get all images from assigned image sets
        assigned_image_ids = []
        for assignment in assignments:
            assigned_image_ids.extend(
                assignment.image_set.images.values_list('id', flat=True)
            )
        
        # Get already evaluated image IDs
        evaluated_image_ids = Evaluation.objects.filter(
            clinician=request.user,
            image__isnull=False
        ).values_list('image_id', flat=True)
        
        # Calculate progress solely based on the current scope (assignments var)
        # If we filtered by assignment_id, this calculates progress for THAT assignment.
        # However, we must ensure evaluated_image_ids are also filtered by this assignment's image set
        # to get correct progress for just this assignment.
        if assignment_id:
             # Get images specifically for these assignments
             scope_image_ids = set(assigned_image_ids)
             evaluated_image_ids = Evaluation.objects.filter(
                clinician=request.user,
                image__id__in=scope_image_ids
            ).values_list('image_id', flat=True)

        # Filter out evaluated images
        remaining_image_ids = set(assigned_image_ids) - set(evaluated_image_ids)
        
        if not remaining_image_ids:
            return JsonResponse({
                'success': True,
                'completed': True,
                'message': 'All assigned images have been evaluated'
            })
        
        # Pick a random image from remaining ones
        selected_image = Image.objects.filter(id__in=remaining_image_ids).order_by('?').first()
        
        if not selected_image:
            return JsonResponse({
                'success': True,
                'completed': True,
                'message': 'No more images to evaluate'
            })
        
        # Calculate progress
        total_assigned = len(assigned_image_ids)
        total_evaluated = len(evaluated_image_ids)
        progress_percentage = (total_evaluated / total_assigned * 100) if total_assigned > 0 else 0
        
        return JsonResponse({
            'success': True,
            'completed': False,
            'image_url': selected_image.file.url,
            'image_id': selected_image.id,
            'remaining': len(remaining_image_ids),
            'progress': {
                'evaluated': total_evaluated,
                'total': total_assigned,
                'percentage': progress_percentage
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

