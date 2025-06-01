from django.urls import path
from .views import test_form_view, AptitudeTestView, dashboard_view

urlpatterns = [
    path('aptitude/', AptitudeTestView.as_view(), name='aptitude-test-api'),
    path('aptitude/form/', test_form_view, name='aptitude-form'),
    path('dashboard/', dashboard_view, name='dashboard'),
]