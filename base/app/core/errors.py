class AppError(Exception):
    status_code = 500


class ProductNotFoundError(AppError):
    status_code = 404
