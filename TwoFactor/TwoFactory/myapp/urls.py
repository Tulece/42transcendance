from django.urls import path
from .views import send_test_email

urlpatterns = [
    path('send_test_email/', send_test_email, name='send_test_email'),
]
