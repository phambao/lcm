from django.contrib.auth.views import LoginView
from django.shortcuts import render, resolve_url
from django.contrib.auth.decorators import login_required

from base.forms import DealerAuthenticationForm


class DealerLoginView(LoginView):
    """
    Display the login form and handle the login action.
    """

    form_class = DealerAuthenticationForm
    authentication_form = None
    template_name = "dealers/login.html"
    redirect_authenticated_user = True
    extra_context = None
    redirect_field_name = 'dealer-dashboard'

    def get_success_url(self):
        return resolve_url('dealer-dashboard')


@login_required(login_url='/dealer/login/')
def dashboard(request):
    return render(request, 'dealers/dashboard.html', {})
