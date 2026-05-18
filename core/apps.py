from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'Sistema Clínico'

    def ready(self):
        """Cargar señales cuando la app está lista"""
        import core.signals
