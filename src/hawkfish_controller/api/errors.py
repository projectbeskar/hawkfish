from fastapi.responses import JSONResponse


def redfish_error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": str(status_code),
                "message": message,
                "@Message.ExtendedInfo": [
                    {"MessageId": "Oem.HawkFish.GeneralError", "Message": message}
                ],
            }
        },
    )


