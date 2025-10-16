# app/core/exceptions.py
class BizException(Exception):
    def __init__(self, code: int = 500, message: str = "业务错误", data: dict | None = None, headers: dict | None = None):
        self.code = code
        self.message = message
        self.data = data
        self.headers = headers
