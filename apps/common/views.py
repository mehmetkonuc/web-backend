from django.shortcuts import render
from django.views import View

# Create your views here.
class TermsOfServiceView(View):
    def get(self, request):
        return render(request, 'pages/terms_of_service.html')

class PrivacyPolicyView(View):
    def get(self, request):
        return render(request, 'pages/privacy_policy.html')