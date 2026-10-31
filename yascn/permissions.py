from rest_framework.permissions import BasePermission, SAFE_METHODS


class CatalogPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and
                    (request.user.role in ("admin", "staff") if request.method in SAFE_METHODS
                     else request.user.role == "admin"))


class SubscriptionPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and
                    (request.method in SAFE_METHODS or request.user.role in ("admin", "staff")))
