from urllib.request import url2pathname
from urllib.parse import urlparse


def path_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError("unsupported scheme: {}".format(parsed.scheme))
    return url2pathname(parsed.path)
