from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import Invitation, Evaluation
import uuid
import json
import os
import random
from django.conf import settings

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
        image_path = data.get('image_path')
        is_real = data.get('is_real')
        confidence = data.get('confidence')
        
        # Validate inputs
        if not image_path or is_real is None or not confidence:
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
        
        # Create evaluation
        evaluation = Evaluation.objects.create(
            clinician=request.user,
            image_path=image_path,
            is_real=is_real,
            confidence=int(confidence)
        )
        
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
        # Get all evaluated images by this user
        evaluated_images = Evaluation.objects.filter(clinician=request.user).values_list('image_path', flat=True)
        
        # Get all available images
        real_images = []
        synth_images = []
        
        if os.path.exists(settings.REAL_IMAGES_DIR):
            real_images = [os.path.join('real', f) for f in os.listdir(settings.REAL_IMAGES_DIR) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if os.path.exists(settings.SYNTH_IMAGES_DIR):
            synth_images = [os.path.join('synth', f) for f in os.listdir(settings.SYNTH_IMAGES_DIR) 
                           if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
        all_images = real_images + synth_images
        
        # Filter out evaluated ones
        remaining_images = [img for img in all_images if img not in evaluated_images]
        
        if not remaining_images:
            return JsonResponse({
                'success': True,
                'completed': True,
                'message': 'All images have been evaluated'
            })
        
        # Pick a random image
        selected_image = random.choice(remaining_images)
        
        return JsonResponse({
            'success': True,
            'completed': False,
            'image_url': f"{settings.MEDIA_URL}{selected_image}",
            'image_path': selected_image,
            'remaining': len(remaining_images)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
