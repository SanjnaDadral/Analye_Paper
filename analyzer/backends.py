from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in with either
    username or email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        # Get the identifier (username or email)
        identifier = username or kwargs.get('email')

        if not identifier or not password:
            return None

        try:
            # Try to find user by username or email (case-insensitive)
            user = UserModel.objects.get(
                Q(username__iexact=identifier) |
                Q(email__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            # In rare case of duplicate, take the first one
            user = UserModel.objects.filter(
                Q(username__iexact=identifier) |
                Q(email__iexact=identifier)
            ).order_by('id').first()

        # Check password and whether user is allowed to authenticate
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None