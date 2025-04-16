class Config:
    # Limit maximum rooms to prevent memory issues
    MAX_ROOMS = 50
    # Maximum clients per room
    MAX_CLIENTS_PER_ROOM = 30
    # Room cleanup time (in seconds)
    ROOM_CLEANUP_TIME = 3600  # 1 hour
    # Session configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour