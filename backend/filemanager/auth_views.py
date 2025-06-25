from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import logging

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    return Response({'message': 'CSRF cookie set'})

@ensure_csrf_cookie
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    logger.info(f"Login attempt for user: {username}")
    logger.info(f"Request data: {request.data}")

    if not username or not password:
        logger.error("Missing username or password")
        return Response(
            {'error': 'Please provide both username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user exists
    try:
        user = User.objects.get(username=username)
        logger.info(f"User {username} exists in database")
    except User.DoesNotExist:
        logger.error(f"User {username} does not exist in database")
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Try to authenticate
    user = authenticate(request, username=username, password=password)
    logger.info(f"Authentication result for {username}: {'Success' if user else 'Failed'}")

    if user is not None:
        if user.is_active:
            login(request, user)
            logger.info(f"Login successful for user: {username}")
            return Response({
                'message': 'Login successful',
                'user': {
                    'username': user.username,
                    'is_superuser': user.is_superuser
                }
            })
        else:
            logger.error(f"User {username} is not active")
            return Response(
                {'error': 'This account is not active'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    else:
        # If authentication failed but user exists, it means password is wrong
        logger.error(f"Invalid password for user: {username}")
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logged out successfully'}) 