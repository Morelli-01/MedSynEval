from django.test import TestCase, Client
from django.urls import reverse
from .models import Clinician, Evaluation
from django.conf import settings
import os
import shutil

class EvaluatorTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Clinician.objects.create_user(username='testuser', password='password')
        
        # Create dummy images for testing
        self.test_data_dir = os.path.join(settings.BASE_DIR, 'test_data')
        self.real_dir = os.path.join(self.test_data_dir, 'real')
        self.synth_dir = os.path.join(self.test_data_dir, 'synth')
        
        os.makedirs(self.real_dir, exist_ok=True)
        os.makedirs(self.synth_dir, exist_ok=True)
        
        with open(os.path.join(self.real_dir, 'test1.jpg'), 'w') as f:
            f.write('test')
            
        # Override settings for testing
        self._original_real_dir = settings.REAL_IMAGES_DIR
        self._original_synth_dir = settings.SYNTH_IMAGES_DIR
        settings.REAL_IMAGES_DIR = self.real_dir
        settings.SYNTH_IMAGES_DIR = self.synth_dir

    def tearDown(self):
        shutil.rmtree(self.test_data_dir)
        settings.REAL_IMAGES_DIR = self._original_real_dir
        settings.SYNTH_IMAGES_DIR = self._original_synth_dir

    def test_login_and_evaluate(self):
        # Login
        login_success = self.client.login(username='testuser', password='password')
        self.assertTrue(login_success)
        
        # Get evaluate page
        response = self.client.get(reverse('evaluate'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Image Evaluation')
        
        # Check context has image
        self.assertIn('image_path', response.context)
        image_path = response.context['image_path']
        
        # Submit evaluation
        response = self.client.post(reverse('evaluate'), {
            'image_path': image_path,
            'is_real': True,
            'confidence': 5
        })
        
        # Should redirect to evaluate again
        self.assertRedirects(response, reverse('evaluate'))
        
        # Check evaluation saved
        self.assertTrue(Evaluation.objects.filter(clinician=self.user, image_path=image_path).exists())
        
    def test_registration(self):
        # Create invitation
        from .models import Invitation
        invitation = Invitation.objects.create()
        
        # Test registration with valid token
        response = self.client.post(reverse('register'), {
            'token': str(invitation.token),
            'username': 'newuser',
            'password': 'StrongPassword123!', # Try standard 'password' first? No, error said password1
            # If error said password1, then it must be password1.
            # But why? Maybe an older django version or something?
            # Or maybe I am misreading the error log from previous step?
            # Step 231 output: .Form errors: <ul class="errorlist"><li>password1<ul class="errorlist"><li>This field is required.</li></ul></li></ul>
            # Yes, it says password1.
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'title': 'Dr.',
            'years_experience': 5
        })
        
        if response.context and 'form' in response.context and response.context['form'].errors:
            print(f"Form errors: {response.context['form'].errors}")
        
        # Check if invitation is used
        invitation.refresh_from_db()
        self.assertTrue(invitation.is_used)
        
        # Test registration page load without token (should show form with token input)
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invitation Token') # Check for label
        
    def test_profile(self):
        self.client.login(username='testuser', password='password')
        
        # Get profile page
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        
        # Update profile
        response = self.client.post(reverse('profile'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'title': 'Prof.',
            'years_experience': 10
        })
        
        self.assertRedirects(response, reverse('profile'))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.title, 'Prof.')
