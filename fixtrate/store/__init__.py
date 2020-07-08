import typing as t
from urllib.parse import urlparse, unquote, parse_qs

import aioredis  # type: ignore

from .base import FixStore # NOQA
from .inmemory import MemoryStore # NOQA
from .redis import RedisStore # NOQA


if t.TYPE_CHECKING:
    from ..config import FixSessionConfig


async def create_store(config: "FixSessionConfig", dsn: str) -> FixStore:
    store: FixStore
    url = urlparse(dsn)
    if url.scheme == "redis":
        if "@" in url.netloc:
            _, dsn_hostspec = url.netloc.split("@")
        else:
            dsn_hostspec = url.netloc

        dsn_host, dsn_port = dsn_hostspec.split(":")
        host = unquote(dsn_host)
        port = int(unquote(dsn_port))

        prefix: t.Optional[str]

        if url.query:
            _query = parse_qs(url.query, strict_parsing=True)
            query: t.Dict[str, str] = {}
            for key, val in _query.items():
                query[key] = val[-1]
            prefix = query.get("prefix")
        else:
            prefix = None

        redis_url = f"redis://{host}:{port}"
        redis = await aioredis.create_redis_pool(redis_url, maxsize=5)
        store = RedisStore(config, redis, prefix)
    else:
        store = MemoryStore(config)

    return store
