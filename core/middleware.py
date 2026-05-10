from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from .models import BannedDevice, DeviceSession


class DeviceBanMiddleware(MiddlewareMixin):
    def process_request(self, request):
        device_id = request.COOKIES.get("device_id")
        if not device_id:
            device = DeviceSession.objects.create()
            request.device_id = str(device.identifier)
            return None
        request.device_id = device_id
        if BannedDevice.objects.filter(identifier=device_id).exists():
            return HttpResponseForbidden("هذا الجهاز محظور من الوصول إلى الموقع.")
        return None

    def process_response(self, request, response):
        if hasattr(request, "device_id") and "device_id" not in request.COOKIES:
            response.set_cookie("device_id", request.device_id, max_age=60 * 60 * 24 * 365)
        return response
