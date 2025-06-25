from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from . import views
from . import auth_views

router = DefaultRouter()
router.register(r'files', views.FileViewSet)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for Docker"""
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health_check, name='health'),
    path('auth/csrf/', auth_views.get_csrf_token, name='csrf'),
    path('auth/login/', auth_views.login_view, name='login'),
    path('auth/logout/', auth_views.logout_view, name='logout'),
] 