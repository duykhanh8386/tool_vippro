# RECOVERED: reconstructed from CPython 3.12 bytecode
import inspect
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Type, Union

from fastapi import Request
from fastapi.responses import PlainTextResponse
from loguru import logger
from nicegui import ui

from src.license_manager import is_licensed, verify_license


@dataclass
class Route:
    path: str
    view_func: Callable
    title: str
    requires_auth: bool = False
    is_async: bool = False
    params: Optional[Dict[str, Type]] = None
    local_only: bool = False


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
        local_only: bool = False,
    ):
        def decorator(view_func: Callable):
            is_async = inspect.iscoroutinefunction(view_func)
            self.routes[path] = Route(
                path=path,
                view_func=view_func,
                title=title,
                is_async=is_async,
                params=params or {},
                local_only=local_only,
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
                    if route.local_only and not self.is_local_request(request):
                        return PlainTextResponse("Local access only", status_code=403)
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
                    if route.local_only and not self.is_local_request(request):
                        return PlainTextResponse("Local access only", status_code=403)
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

    @staticmethod
    def is_local_request(request: Request) -> bool:
        try:
            return bool(request.client and ipaddress.ip_address(request.client.host).is_loopback)
        except ValueError:
            return False

    def is_authenticated(self) -> bool:
        """Check if user has a valid license."""
        return is_licensed()

    def verify_activation_key(self, license_key: str) -> tuple[bool, str]:
        """Validate and activate a Keygen license for this device."""
        return verify_license(license_key)

    def handle_unauthorized(self):
        """Handle unauthorized access attempts"""
        return ui.navigate.to(self.login_path)


router = RouterManager()
