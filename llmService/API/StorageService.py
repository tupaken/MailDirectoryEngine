import json
import os
from urllib import error, request

STORAGE_SERVICE_ENDPOINT = os.getenv("STORAGE_SERVICE_ENDPOINT")

def send_storage_payload(source_path:str,number:str):
    endpoint = STORAGE_SERVICE_ENDPOINT
    if not endpoint:
        raise RuntimeError ("STORAGE_SERVICE_ENDPOINT is empty")
    
    timeout =  int(os.getenv("STORAGE_SERVICE_TIMEOUT_SECONDS", "30"))

    payload={
        "sourcePath":source_path,
        "number":number,
    }

    req= request.Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json"},
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            body=response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_text=exc.read().decode("utf-8",errors="replace")
        raise RuntimeError(
            f"StorageService returned HTTP {exc.code} for {endpoint}: {error_text}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError (
            f"Could not reach StorageService endpoint {endpoint}: {exc}"
        )from exc
    
    return json.loads(body)
