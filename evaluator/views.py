import os
import random
import uuid as uuid_lib
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .forms import ClinicianRegistrationForm, EvaluationForm, ClinicianProfileForm
from .models import Evaluation, Invitation, Assignment, Image, ImageSet

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
    # Get all active assignments for this clinician
    assignments = Assignment.objects.filter(
        clinician=request.user,
        image_set__is_active=True,
        is_completed=False
    ).select_related('image_set')
    
    if not assignments.exists():
        # Check if there are any completed assignments
        completed_assignments = Assignment.objects.filter(
            clinician=request.user,
            is_completed=True
        ).exists()
        
        if completed_assignments:
            return render(request, 'evaluator/done.html', {
                'message': 'You have completed all your assigned evaluations!'
            })
        else:
            return render(request, 'evaluator/done.html', {
                'message': 'You have no image sets assigned for evaluation. Please contact your administrator.'
            })
    
    # Determine which assignment to use
    selected_assignment_id = request.GET.get('assignment')
    if selected_assignment_id:
        try:
            selected_assignment = assignments.get(id=selected_assignment_id)
        except Assignment.DoesNotExist:
            messages.error(request, 'Invalid assignment selected.')
            return redirect('evaluate')
    else:
        # Default to the first assignment
        selected_assignment = assignments.first()

    # Get all images from the selected assignment's image set
    assigned_image_ids = list(selected_assignment.image_set.images.values_list('id', flat=True))
    
    # Get already evaluated image IDs
    evaluated_image_ids = Evaluation.objects.filter(
        clinician=request.user,
        image__isnull=False,
        image__image_set=selected_assignment.image_set # Filter by current assignment's image set
    ).values_list('image_id', flat=True)
    
    # Filter out evaluated images
    remaining_image_ids = set(assigned_image_ids) - set(evaluated_image_ids)
    
    if not remaining_image_ids:
        # Mark selected assignment as completed if progress is 100%
        if selected_assignment.get_progress() == 100:
            selected_assignment.is_completed = True
            selected_assignment.completed_at = timezone.now()
            selected_assignment.save()
        
        # If user has other incomplete assignments, suggest switching instead of showing done page immediately?
        # For now, show done message but maybe with a link to others if we were fancy.
        # But wait, if they strictly want to evaluate, blocking them might be annoying if they just finished one.
        # Let's just show done for THIS assignment. They can switch via the UI if we add it to done.html,
        # or we just redirect to evaluate (which defaults to first incomplete).
        # Actually, if this one is done, let's just let the view handle it.
        # If we redirect to 'evaluate' without param, it picks the first one.
        # If the first one is the one we just finished, we loop.
        # Assignments query filters `is_completed=False`. So if we mark it complete, it disappears from `assignments`.
        # So redirecting to 'evaluate' will pick the next incomplete one!
        return redirect('evaluate')
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.clinician = request.user
            
            # Get the image ID from the hidden field
            image_id = request.POST.get('image_id')
            
            try:
                image = Image.objects.get(id=image_id)
                
                # Verify this image is in one of the user's assignments
                if image.id not in assigned_image_ids:
                    messages.error(request, 'Invalid image selection.')
                    return redirect(f'/evaluate/?assignment={selected_assignment.id}')
                
                # Check if already evaluated
                if Evaluation.objects.filter(clinician=request.user, image=image).exists():
                    messages.warning(request, 'You have already evaluated this image.')
                    return redirect(f'/evaluate/?assignment={selected_assignment.id}')
                
                evaluation.image = image
                evaluation.save()
                
                # Check if selected assignment is now complete
                if selected_assignment.get_progress() == 100 and not selected_assignment.is_completed:
                    selected_assignment.is_completed = True
                    selected_assignment.completed_at = timezone.now()
                    selected_assignment.save()
                    # If complete, redirect to base evaluate to pick next one
                    return redirect('evaluate')
                
                return redirect(f'/evaluate/?assignment={selected_assignment.id}')
                
            except Image.DoesNotExist:
                messages.error(request, 'Invalid image.')
                return redirect(f'/evaluate/?assignment={selected_assignment.id}')
    else:
        # Pick a random image from remaining ones
        selected_image = Image.objects.filter(id__in=remaining_image_ids).order_by('?').first()
        
        if not selected_image:
             # Should be covered by remaining_image_ids check above, but purely defensive:
             return redirect('evaluate')
        
        form = EvaluationForm()
        
        # Calculate progress
        total_assigned = len(assigned_image_ids)
        total_evaluated = len(evaluated_image_ids)
        progress_percentage = (total_evaluated / total_assigned * 100) if total_assigned > 0 else 0
        
        context = {
            'image_url': selected_image.file.url,
            'image_id': selected_image.id,
            'form': form,
            'progress': {
                'evaluated': total_evaluated,
                'total': total_assigned,
                'percentage': progress_percentage
            },
            'assignments': assignments,
            'selected_assignment': selected_assignment,
        }
        return render(request, 'evaluator/evaluate.html', context)

    return render(request, 'evaluator/evaluate.html', {'form': form})


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
    """Admin panel showing per-assignment evaluation statistics"""
    # Check if user is admin/superuser
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    from django.db.models import Count, Avg, Q
    from .models import Clinician
    
    # Get all assignments with related data
    assignments = Assignment.objects.select_related(
        'clinician', 'image_set', 'assigned_by'
    ).prefetch_related('image_set__images').all()
    
    assignments_data = []
    
    for assignment in assignments:
        # Get evaluations for this specific assignment
        evaluations = Evaluation.objects.filter(
            clinician=assignment.clinician,
            image__image_set=assignment.image_set
        ).select_related('image')
        
        total = evaluations.count()
        total_images = assignment.image_set.images.count()
        
        if total == 0:
            # Assignment not started yet
            assignments_data.append({
                'assignment_id': assignment.id,
                'clinician': assignment.clinician,
                'image_set': assignment.image_set,
                'assigned_at': assignment.assigned_at,
                'assigned_by': assignment.assigned_by,
                'is_completed': assignment.is_completed,
                'completed_at': assignment.completed_at,
                'total_images': total_images,
                'total_evaluations': 0,
                'progress': 0,
                'accuracy': None,
                'real_accuracy': None,
                'synth_accuracy': None,
                'avg_confidence': None,
                'confidence_dist': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            })
            continue
        
        # Calculate accuracy metrics
        correct = 0
        real_evaluated = 0
        real_correct = 0
        synth_evaluated = 0
        synth_correct = 0
        
        # Confidence distribution
        confidence_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for eval in evaluations:
            # Get the actual image type
            is_real_image = eval.image.is_real
            
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
        real_accuracy = (real_correct / real_evaluated * 100) if real_evaluated > 0 else None
        synth_accuracy = (synth_correct / synth_evaluated * 100) if synth_evaluated > 0 else None
        progress = (total / total_images * 100) if total_images > 0 else 0
        
        # Calculate average confidence
        avg_confidence = evaluations.aggregate(Avg('confidence'))['confidence__avg'] or 0
        
        # Convert confidence counts to percentages
        confidence_dist = {}
        for level in range(1, 6):
            confidence_dist[level] = (confidence_counts[level] / total * 100) if total > 0 else 0
        
        assignments_data.append({
            'assignment_id': assignment.id,
            'clinician': assignment.clinician,
            'image_set': assignment.image_set,
            'assigned_at': assignment.assigned_at,
            'assigned_by': assignment.assigned_by,
            'is_completed': assignment.is_completed,
            'completed_at': assignment.completed_at,
            'total_images': total_images,
            'total_evaluations': total,
            'progress': progress,
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
    
    # Sort by assignment date (most recent first)
    assignments_data.sort(key=lambda x: x['assigned_at'], reverse=True)
    
    # Calculate overall statistics
    total_assignments = len(assignments_data)
    completed_assignments = sum(1 for a in assignments_data if a['is_completed'])
    total_evaluations = sum(a['total_evaluations'] for a in assignments_data)
    
    # Calculate overall accuracy (only for assignments with evaluations)
    assignments_with_evals = [a for a in assignments_data if a['total_evaluations'] > 0]
    if assignments_with_evals:
        overall_accuracy = sum(a['accuracy'] * a['total_evaluations'] for a in assignments_with_evals) / total_evaluations
    else:
        overall_accuracy = 0
    
    context = {
        'assignments': assignments_data,
        'total_assignments': total_assignments,
        'completed_assignments': completed_assignments,
        'in_progress_assignments': total_assignments - completed_assignments,
        'total_evaluations': total_evaluations,
        'overall_accuracy': overall_accuracy,
    }
    
    return render(request, 'evaluator/admin_panel.html', context)

