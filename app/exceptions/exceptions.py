from fastapi import status
from typing import Optional

class ServiceError(Exception):
    """Base class for all service-related errors."""
    def __init__(self, detail: Optional[str] = None, status_code: Optional[int] = None):
        self.detail = detail or "An unexpected error occurred."
        self.status_code = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR

class UserAlreadyExistsError(ServiceError):
    def __init__(self, detail: str = "User already exists."):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)

class AuthenticationError(ServiceError):
    def __init__(self, detail: str = "Authentication failed."):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class IncorrectPasswordError(ServiceError):
    def __init__(self, detail: str = "Incorrect password."):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class FileError(ServiceError):
    def __init__(self, detail: str = "File operation failed."):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)

class FileProcessingError(ServiceError):
    def __init__(self, detail: str = "Upload processing failed."):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EncryptionServiceError(ServiceError):
    def __init__(self, detail: str = "Encryption error."):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DatabaseError(ServiceError):
    def __init__(self, detail: str = "Database error."):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class JourneyNotFoundError(ServiceError):
    def __init__(self, detail: str = "Journey not found."):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class RouteNotFoundError(ServiceError):
    def __init__(self, detail: str = "Route not found."):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class TokenExpiredError(ServiceError):
    def __init__(self, detail: str = "Token expired."):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class InvalidTokenError(ServiceError):
    def __init__(self, detail: str = "Invalid token."):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class JourneyError(ServiceError):
    def __init__(self, detail: str = "Journey error.", status_code: int = 400):
        super().__init__(detail=detail, status_code=status_code)

class JourneyStartFailed(ServiceError):
    def __init__(self, detail: str = "Failed to start journey.", status_code: int = 500):
        super().__init__(detail=detail, status_code=status_code)


class NoActiveJourney(ServiceError):
    def __init__(self, detail: str = "No active journey found.", status_code: int = 404):
        super().__init__(detail=detail, status_code=status_code)
    
class PushNotificationFailed(ServiceError):
    def __init__(self, detail: str = "Need both start and end stop to begin journey."):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WebsocketBroadcastFailed(ServiceError):
    def __init__(self, detail: str = "Need both start and end stop to begin journey."):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RouteNotFoundError(ServiceError):
    def __init__(self, detail: str = "Route not found."):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class JourneyNotFoundError(ServiceError):
    def __init__(self, detail: str = "Journey not found."):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class AnchorUpdateError(ServiceError):
    def __init__(self, detail: str = "Failed to update arrival anchor."):
        super().__init__(detail=detail, status_code=500)

class IncorrectPasswordError(ServiceError):
    def __init__(self, detail: str = "Incorrect password."):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)

class UserNotFoundError(ServiceError):
    def __init__(self, detail: str = "User not found."):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)