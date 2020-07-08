import typing as t
from urllib.parse import urlparse, parse_qs, unquote


FIX_VERSIONS = {"4.2", "4.4"}
MISSING = "Missing value for '%s'"
DEFAULT_FIX_VERSION = "4.2"


class FixSessionConfig:

    __slots__ = (
        "host",
        "port",
        "version",
        "sender",
        "target",
        "hb_int",
        "qualifier",
        "account",
    )

    def __init__(
        self,
        host: str,
        port: int,
        version: str,
        sender: str,
        target: str,
        hb_int: int,
        qualifier: str,
        account: t.Optional[str],
    ):
        self.host = host
        self.port = port
        self.version = version
        self.sender = sender
        self.target = target
        self.hb_int = hb_int
        self.qualifier = qualifier
        self.account = account

    def asdict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "version": self.version,
            "sender": self.sender,
            "target": self.target,
            "hb_int": self.hb_int,
            "qualifier": self.qualifier,
            "account": self.account,
        }


def parse_conn_args(
    dsn: t.Optional[str] = None,
    version: t.Optional[str] = None,
    host: t.Optional[str] = None,
    port: t.Optional[int] = None,
    sender: t.Optional[str] = None,
    target: t.Optional[str] = None,
    hb_int: t.Optional[int] = None,
    qualifier: str = None,
    account: t.Optional[str] = None,
) -> FixSessionConfig:

    if dsn:
        url = urlparse(dsn)
        scheme = url.scheme.split("+")

        if len(scheme) == 1:
            fix_str = scheme[0]
            dsn_version = DEFAULT_FIX_VERSION
        elif len(scheme) == 2:
            fix_str, dsn_version = scheme
            if fix_str != "fix":
                raise ValueError(
                    f"Scheme '{url.scheme}' is not valid, "
                    "scheme must be of form 'fix+[version]'"
                )
        else:
            raise ValueError(
                f"Scheme '{url.scheme}' is not valid, "
                "scheme must be of form 'fix[+[version]]'"
            )

        if version is None and dsn_version:
            version = dsn_version

        if url.netloc:
            if "@" in url.netloc:
                dsn_auth, dsn_hostspec = url.netloc.split("@")
            else:
                dsn_hostspec = url.netloc
                dsn_auth = ""
        else:
            dsn_auth = dsn_hostspec = ""

        if dsn_auth:
            dsn_sender, dsn_target = dsn_auth.split(":")
        else:
            dsn_sender = dsn_target = ""

        if sender is None and dsn_sender:
            sender = unquote(dsn_sender)

        if target is None and dsn_target:
            target = unquote(dsn_target)

        if dsn_hostspec:
            addr = dsn_hostspec.split(":")
            if len(addr) != 2:
                raise ValueError(
                    "DSN hostpect must be of form '[host]:[port]'")
            dsn_host, dsn_port = addr

        if host is None and dsn_host:
            host = unquote(dsn_host)

        if port is None and dsn_port:
            port = int(unquote(dsn_port))

        if url.query:
            _query = parse_qs(url.query, strict_parsing=True)
            query: t.Dict[str, str] = {}
            for key, val in _query.items():
                query[key] = val[-1]
            if account is None and "account" in query:
                account = query["account"]
            if qualifier is None and "qualifier" in query:
                qualifier = query["qualifier"]
            if hb_int is None and "hb_int" in query:
                hb_int = int(query["hb_int"])

    if not host:
        raise ValueError(MISSING % "host")

    if not port:
        raise ValueError(MISSING % "port")

    if not version:
        raise ValueError(MISSING % "version")

    if not sender:
        raise ValueError(MISSING % "sender")

    if not target:
        raise ValueError(MISSING % "target")

    if not qualifier:
        qualifier = ""

    if version not in FIX_VERSIONS:
        raise ValueError(
            f"{version} is not a valid FIX version ,"
            f"please specify one of: {' ,'.join(FIX_VERSIONS)}"
        )

    version = f"FIX.{version}"

    if hb_int is None:
        hb_int = 30

    return FixSessionConfig(
        host=host,
        port=port,
        version=version,
        sender=sender,
        target=target,
        hb_int=hb_int,
        qualifier=qualifier,
        account=account,
    )
