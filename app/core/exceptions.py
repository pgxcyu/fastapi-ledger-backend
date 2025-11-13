# app/core/exceptions.py
class AppBaseException(Exception):
    """应用内所有自定义异常的基类"""
    status_code: int = 500
    code: int
    message: str
    data: dict | None = None
    headers: dict | None = None

class BizException(AppBaseException):
    def __init__(self, code: int = 500, message: str = "业务错误", data: dict | None = None, headers: dict | None = None):
        self.code = code
        self.message = message
        self.data = data
        self.headers = headers
        super().__init__(self.message)
