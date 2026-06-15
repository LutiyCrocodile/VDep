"""
Custom authentication for Django REST Framework using auth-service
"""
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import async_to_sync

from .auth_client import auth_client


class AuthServiceAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication that validates JWT tokens with auth-service
    """
    
    def authenticate(self, request):
        # Get Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        # Verify token with auth-service (async function called in sync context)
        user_data = async_to_sync(auth_client.verify_token)(token)
        
        if not user_data:
            raise AuthenticationFailed('Invalid or expired token')
        
        # Check if user has access to dashboard service
        dashboard_access = user_data.get('services', {}).get('dashboard', {})
        
        if not dashboard_access or not dashboard_access.get('role'):
            raise AuthenticationFailed('No access to dashboard service')
        
        # Create a simple user object with the data from auth-service
        user = AuthUser(
            id=user_data.get('id'),
            username=user_data.get('username'),
            email=user_data.get('email'),
            full_name=user_data.get('full_name'),
            is_employee=user_data.get('is_employee', False),
            dashboard_role=dashboard_access.get('role'),
            dashboard_perms=dashboard_access.get('perms', []),
        )
        
        return (user, token)


class AuthUser:
    """
    Simple user object for auth-service integration
    """
    
    def __init__(self, id, username, email, full_name, is_employee, dashboard_role, dashboard_perms):
        self.id = id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.is_employee = is_employee
        self.dashboard_role = dashboard_role
        self.dashboard_perms = dashboard_perms
        self.is_authenticated = True
        self.is_anonymous = False
    
    def __str__(self):
        return self.username
    
    def has_perm(self, perm):
        """Check if user has a specific permission"""
        return perm in self.dashboard_perms
    
    def has_perms(self, perms):
        """Check if user has all specified permissions"""
        return all(perm in self.dashboard_perms for perm in perms)
    
    def has_role(self, role):
        """Check if user has a specific role"""
        return self.dashboard_role == role
