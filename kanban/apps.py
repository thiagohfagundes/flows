from django.apps import AppConfig


class KanbanConfig(AppConfig):
    name = 'kanban'
    def ready(self):
        import kanban.signals  # noqa
