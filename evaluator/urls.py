from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('evaluate/', views.evaluate_image, name='evaluate'),
    path('profile/', views.profile, name='profile'),
    path('api/validate-token/', api_views.validate_token, name='validate_token'),
    path('api/submit-evaluation/', api_views.submit_evaluation, name='submit_evaluation'),
    path('api/get-next-image/', api_views.get_next_image, name='get_next_image'),
    path('', views.landing, name='home'),
]
