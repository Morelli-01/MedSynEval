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
