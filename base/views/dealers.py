from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.shortcuts import render, resolve_url, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from base.forms import DealerAuthenticationForm
from base.models.payment import DealerInformation, DealerCompany


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
    data_dealer = DealerInformation.objects.get(user=request.user)
    dealers = DealerCompany.objects.filter(dealer=data_dealer)
    token = request.session.get('token')
    dealer_companies = DealerCompany.objects.filter(
        dealer=data_dealer,
    )
    total = 0
    temp = []

    paginator = Paginator(dealers, 10)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    for dealer in dealer_companies:
        if dealer.referral_code.id not in temp:
            total += 1
            temp.append(dealer.referral_code.id)
    context = {
        'dealers': dealers,
        'data_dealer': data_dealer,
        'total_referral_code': total,
        'total_new_user': len(dealers),
        "page_obj": page_obj
    }
    return render(request, 'dealers/dashboard.html', context)


def logout_view(request):
    logout(request)
    return redirect('dealer-login')


@login_required(login_url='/dealer/login/')
def orders(request):
    return render(request, 'dealers/dealers.html', {})



