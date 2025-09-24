from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import get_language
from django.views import View


class DashBoardView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'dashboard.html', context)

class MembersView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'members.html', context)

class BillingView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'billing.html', context)

class ExpensesView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'expenses.html', context)

class BalanceView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'balance.html', context)

class PlanView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        language = get_language()  # obtiene el idioma activo del usuario

        # Obtener el host y esquema
        scheme = self.request.scheme
        host = self.request.get_host()

        # Obtener la ruta actual EXACTA (preservando el idioma)
        path = self.request.path

        # Construir la URL base correctamente
        base_url = f"{scheme}://{host}{path}"

        # Iniciar con la URL base como canónica
        canonical_url = base_url

        context = {
            'canonical_url': canonical_url,
        }

        return render(request, 'plan.html', context)
