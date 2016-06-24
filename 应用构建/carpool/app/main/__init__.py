from flask import Blueprint

from app.models import Permission

main = Blueprint('main', __name__)

@main.app_context_processor #上下文管理器，能让变量在所有模板中全局可访问
def inject_permissions():
    return dict(Permission=Permission)

from . import views, errors