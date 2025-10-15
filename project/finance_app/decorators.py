import jwt
from functools import wraps
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.session.get('access_token')
        if not token:
            messages.error(request, 'Please log in first.')
            return redirect('login')

        try:
           jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            messages.error(request, 'Session expired. Please log in again.')
            return redirect('login')
        except jwt.InvalidTokenError:
            messages.error(request, 'Invalid session. Please log in again.')
            return redirect('login')

        return view_func(request, *args, **kwargs)

    return wrapper
