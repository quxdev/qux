from django.apps import AppConfig


class QueuedTasks(AppConfig):
    name = "qux.tasks"
    label = "qux_tasks"
    verbose_name = "Queued Tasks"
