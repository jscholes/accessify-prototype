class APIError(Exception):
    def __init__(self, status_code, error_message, *args, **kwargs):
        self.status_code = status_code
        self.error_message = error_message


class AuthorisationError(Exception):
    def __init__(self, error_id, error_description, *args, **kwargs):
        self.error_id = error_id
        self.error_description = error_description

