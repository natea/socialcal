import logging
import traceback
import sys
from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from django.template.loader import render_to_string
from django.views.debug import ExceptionReporter

logger = logging.getLogger('django.request')

class ExceptionLoggingMiddleware:
    """
    Middleware that logs exceptions and provides detailed error information in development.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Process exceptions and log detailed information.
        """
        # Get the exception info
        exc_info = sys.exc_info()
        
        # Get user info safely
        user_info = "AnonymousUser"
        if hasattr(request, 'user'):
            user_info = str(request.user)
        
        # Log the exception with detailed information
        logger.error(
            f'Exception caught in {request.path}\n'
            f'Method: {request.method}\n'
            f'GET params: {request.GET}\n'
            f'POST params: {request.POST}\n'
            f'User: {user_info}\n'
            f'Exception: {exception.__class__.__name__}: {exception}',
            exc_info=exc_info,
            extra={
                'status_code': 500,
                'request': request,
            }
        )
        
        # In development, return detailed error information
        if settings.DEBUG:
            reporter = ExceptionReporter(request, *exc_info)
            html = reporter.get_traceback_html()
            
            # Make sure the exception message is included in the response
            # This is important for our tests to verify the middleware is working
            if str(exception) not in html:
                html = f"<h1>Exception: {exception}</h1>\n" + html
                
            return HttpResponseServerError(html, content_type='text/html')
        
        # In production, log but don't expose details
        return None  # Let Django's built-in handler take over 