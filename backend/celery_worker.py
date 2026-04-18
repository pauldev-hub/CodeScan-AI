from app import celery_app, create_app


flask_app = create_app()

# Ensure app context and tasks are registered when worker starts.
flask_app.app_context().push()

celery = flask_app.extensions["celery"]
worker = celery

__all__ = ["celery", "worker", "celery_app"]
