from django.apps import AppConfig


class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'
    verbose_name = 'Paper Analyzer'

    def ready(self):
        # Start the self-ping thread to keep Render free tier awake.
        # Guard against double-execution (Django calls ready() twice in dev
        # with the reloader — RUN_MAIN prevents the second call from spawning
        # a duplicate thread).
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            from .ping import start_ping_thread
            start_ping_thread()
