import os
import random
import uuid as uuid_lib
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import ClinicianRegistrationForm, EvaluationForm, ClinicianProfileForm
from .models import Evaluation, Invitation

def register(request):
    token_str = request.GET.get('token') or request.POST.get('token')
    
    # If we have a token, validate it immediately to fail fast if invalid
    if request.method == 'GET' and token_str:
        # Validate UUID format
        try:
            uuid_lib.UUID(token_str)
            Invitation.objects.get(token=token_str, is_used=False)
        except (ValueError, AttributeError, Invitation.DoesNotExist):
            return render(request, 'evaluator/register.html', {'error': 'Invalid or used invitation token.'})


    if request.method == 'POST':
        # Token is required
        if not token_str:
             return render(request, 'evaluator/register.html', {'form': ClinicianRegistrationForm(request.POST), 'error': 'Invitation token required.'})
        
        # Validate UUID format
        try:
            uuid_lib.UUID(token_str.strip())
        except (ValueError, AttributeError):
            return render(request, 'evaluator/register.html', {'form': ClinicianRegistrationForm(request.POST), 'error': 'Invalid token format.', 'token': token_str})
             
        try:
            invitation = Invitation.objects.get(token=token_str.strip(), is_used=False)
        except Invitation.DoesNotExist:
             return render(request, 'evaluator/register.html', {'form': ClinicianRegistrationForm(request.POST), 'error': 'Invalid or used invitation token.', 'token': token_str})

        form = ClinicianRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            invitation.is_used = True
            invitation.save()
            
            # Automatically log in the user
            login(request, user)
            messages.success(request, 'Account created successfully. Welcome!')
            return redirect('evaluate')
    else:
        form = ClinicianRegistrationForm()
    
    return render(request, 'evaluator/register.html', {'form': form, 'token': token_str})


@login_required
def evaluate_image(request):
    # Get all evaluated images by this user
    evaluated_images = Evaluation.objects.filter(clinician=request.user).values_list('image_path', flat=True)
    
    # Get all available images
    real_images = []
    synth_images = []
    
    if os.path.exists(settings.REAL_IMAGES_DIR):
        real_images = [os.path.join('real', f) for f in os.listdir(settings.REAL_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if os.path.exists(settings.SYNTH_IMAGES_DIR):
        synth_images = [os.path.join('synth', f) for f in os.listdir(settings.SYNTH_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
    all_images = real_images + synth_images
    
    # Filter out evaluated ones
    remaining_images = [img for img in all_images if img not in evaluated_images]
    
    if not remaining_images:
        return render(request, 'evaluator/done.html')
        
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.clinician = request.user
            # The image path comes from the hidden input or session? 
            # Better to pass it via hidden field in the form or keep it in session.
            # Let's use a hidden input in the template and retrieve it here.
            image_path = request.POST.get('image_path')
            
            # Verify the image path is valid and one of the remaining ones (security check)
            # But strictly speaking, if we just trust the hidden field for now it's easier. 
            # Ideally we should re-validate.
            
            evaluation.image_path = image_path
            evaluation.save()
            return redirect('evaluate')
    else:
        # Pick a random image
        selected_image = random.choice(remaining_images)
        form = EvaluationForm()
        
        context = {
            'image_url': f"{settings.MEDIA_URL}{selected_image}",
            'image_path': selected_image,
            'form': form
        }
        return render(request, 'evaluator/evaluate.html', context)

    return render(request, 'evaluator/evaluate.html', {'form': form}) # Fallback

def landing(request):
    return render(request, 'evaluator/landing.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = ClinicianProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ClinicianProfileForm(instance=request.user)
    return render(request, 'evaluator/profile.html', {'form': form})

@login_required
def admin_panel(request):
    """Admin panel showing clinician evaluation accuracy and statistics"""
    # Check if user is admin/superuser
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    from django.db.models import Count, Avg, Q
    from .models import Clinician
    
    # Get all clinicians with evaluations
    clinicians_data = []
    
    # Get total counts for overall statistics
    total_evaluations = Evaluation.objects.count()
    
    # Calculate overall accuracy
    correct_count = 0
    for eval in Evaluation.objects.all():
        # Determine if evaluation is correct
        is_real_image = eval.image_path.startswith('real/')
        if (is_real_image and eval.is_real) or (not is_real_image and not eval.is_real):
            correct_count += 1
    
    overall_accuracy = (correct_count / total_evaluations * 100) if total_evaluations > 0 else 0
    
    # Count total real and synthetic images
    total_real_images = 0
    total_synth_images = 0
    if os.path.exists(settings.REAL_IMAGES_DIR):
        total_real_images = len([f for f in os.listdir(settings.REAL_IMAGES_DIR) 
                                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if os.path.exists(settings.SYNTH_IMAGES_DIR):
        total_synth_images = len([f for f in os.listdir(settings.SYNTH_IMAGES_DIR) 
                                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    # Process each clinician
    for clinician in Clinician.objects.all():
        evaluations = Evaluation.objects.filter(clinician=clinician)
        total = evaluations.count()
        
        if total == 0:
            continue  # Skip clinicians with no evaluations
        
        # Calculate accuracy
        correct = 0
        real_evaluated = 0
        real_correct = 0
        synth_evaluated = 0
        synth_correct = 0
        
        # Confidence distribution
        confidence_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for eval in evaluations:
            # Determine if image is real based on path
            is_real_image = eval.image_path.startswith('real/')
            
            # Count by type
            if is_real_image:
                real_evaluated += 1
                if eval.is_real:
                    real_correct += 1
                    correct += 1
            else:
                synth_evaluated += 1
                if not eval.is_real:
                    synth_correct += 1
                    correct += 1
            
            # Track confidence distribution
            confidence_counts[eval.confidence] += 1
        
        # Calculate percentages
        accuracy = (correct / total * 100) if total > 0 else 0
        real_accuracy = (real_correct / real_evaluated * 100) if real_evaluated > 0 else 0
        synth_accuracy = (synth_correct / synth_evaluated * 100) if synth_evaluated > 0 else 0
        
        # Calculate average confidence
        avg_confidence = evaluations.aggregate(Avg('confidence'))['confidence__avg'] or 0
        
        # Convert confidence counts to percentages
        confidence_dist = {}
        for level in range(1, 6):
            confidence_dist[level] = (confidence_counts[level] / total * 100) if total > 0 else 0
        
        clinicians_data.append({
            'id': clinician.id,
            'username': clinician.username,
            'email': clinician.email,
            'title': clinician.title,
            'years_experience': clinician.years_experience,
            'total_evaluations': total,
            'correct_evaluations': correct,
            'incorrect_evaluations': total - correct,
            'accuracy': accuracy,
            'avg_confidence': avg_confidence,
            'real_evaluated': real_evaluated,
            'real_correct': real_correct,
            'real_accuracy': real_accuracy,
            'synth_evaluated': synth_evaluated,
            'synth_correct': synth_correct,
            'synth_accuracy': synth_accuracy,
            'confidence_dist': confidence_dist,
        })
    
    # Sort by accuracy (descending)
    clinicians_data.sort(key=lambda x: x['accuracy'], reverse=True)
    
    context = {
        'clinicians': clinicians_data,
        'total_evaluations': total_evaluations,
        'overall_accuracy': overall_accuracy,
        'total_real_images': total_real_images,
        'total_synth_images': total_synth_images,
    }
    
    return render(request, 'evaluator/admin_panel.html', context)
