
class DomainError(Exception):
    def __init__(self, code: str, message: str| None):
        self.code = code
        self.message = message
        super().__init__(self.message)


class ValidationError(DomainError):
    pass

class NotFoundError(DomainError):
    pass

class ConflictError(DomainError):
    pass
