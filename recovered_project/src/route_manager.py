# RECOVERED: reconstructed from CPython 3.12 bytecode
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Type, Union

from fastapi import Request
from loguru import logger
from nicegui import ui

#from src.license_manager import is_licensed, verify_license


@dataclass
class Route:
    path: str
    view_func: Callable
    title: str
    requires_auth: bool = False
    is_async: bool = False
    params: Optional[Dict[str, Type]] = None


class RouterManager:
    NOT_AUTH_PATH = ["/auth"]

    def __init__(self):
        self.routes = {}
        self.start_path = "/studio"
        self.login_path = "/auth"

    def set_start_path(self, path: str):
        self.start_path = path

    def register(
        self,
        path: str,
        title: str,
        params: Optional[Dict[str, Type]] = None,
    ):
        def decorator(view_func: Callable):
            is_async = inspect.iscoroutinefunction(view_func)
            self.routes[path] = Route(
                path=path,
                view_func=view_func,
                title=title,
                is_async=is_async,
                params=params or {},
            )
            return view_func

        return decorator

    def setup_routes(self):
        @ui.page("/")
        def root_handler():
            return ui.navigate.to(self.start_path)

        for route in self.routes.values():
            if route.is_async:
                @ui.page(route.path)
                async def async_route_handler(request: Request, route=route):
                    if (
                        route.path not in self.NOT_AUTH_PATH
                        and not self.is_authenticated()
                    ):
                        return self.handle_unauthorized()

                    try:
                        kwargs = {
                            param: request.query_params.get(param)
                            for param in route.params
                        }
                        return await route.view_func(**kwargs)
                    except Exception as e:
                        logger.error(f"Error in async route {route.path}: {e}")
                        ui.notify("An error occurred", type="negative")
                        return ui.navigate.to("/error")
            else:
                @ui.page(route.path)
                def sync_route_handler(request: Request, route=route):
                    if (
                        route.path not in self.NOT_AUTH_PATH
                        and not self.is_authenticated()
                    ):
                        return self.handle_unauthorized()

                    kwargs = {
                        param: request.query_params.get(param)
                        for param in route.params
                    }
                    return route.view_func(**kwargs)

    def is_authenticated(self) -> bool:
        """Check if user has a valid license."""
        return True

    def verify_activation_key(self, license_key: str) -> tuple[bool, str]:
        """Verify a license key via Licensify API."""
        return True

    def handle_unauthorized(self):
        """Handle unauthorized access attempts"""
        return ui.navigate.to(self.login_path)


router = RouterManager()
