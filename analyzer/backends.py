from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either their
    username or their email address.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            # Try to fetch the user by searching the username or email field
            # We use iexact for case-insensitive matching
            user = UserModel.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # If multiple users are found (e.g. same email), take the first one
            user = UserModel.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).order_by('id').first()
            
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
