class BusinessError(Exception):
    def __init__(self, message, status=422, details=None):
        self.message, self.status, self.details = message, status, details


def require(condition, message, status=422):
    if not condition:
        raise BusinessError(message, status)
