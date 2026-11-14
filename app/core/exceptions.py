from fastapi import HTTPException

def not_found(message: str = "Resource not found") -> HTTPException: return HTTPException(status_code=404, detail=message)
def forbidden(message: str = "Not permitted") -> HTTPException: return HTTPException(status_code=403, detail=message)
def conflict(message: str) -> HTTPException: return HTTPException(status_code=409, detail=message)
