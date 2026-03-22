
class TechTrendError(Exception):
    """Base exception class for this project"""
    pass

class ConfigurationError(TechTrendError):
    """設定ファイルに関するエラーを補足する"""
    def __init__(self, message:str, original_error:Exception | None = None):
        super().__init__(message)
        self.original_error = original_error