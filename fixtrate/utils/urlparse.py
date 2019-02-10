from urllib import parse as _urlparse


def register_scheme(scheme):
    for method in filter(lambda s: s.startswith('uses_'), dir(urlparse)):
        uses = getattr(urlparse, method)
        if scheme not in uses:
            uses.append(scheme)


urlparse = _urlparse.urlparse
