# aiohttp_https_proxy

This library created to allow usage of Secure Web Proxy with aiohttp library.
It only works with uvloop now due to inability of `loop.start_tls()` to start tls in tls connection with standard asyncio loop
(for updates on this you can check [this issue](https://bugs.python.org/issue37179)).

Requirements
------------
* aiohttp
* uvloop

Usage
-----
To use this library import `HTTPSProxyConnector` and use it in `aiohttp.ClientSession`. 
Then session can be used as any other aiohttp session:
```
from aiohttp_https_proxy import HTTPSProxyConnector

connector = HTTPSProxyConnector(proxy, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as response:
        ...
```

`HTTPSProxyConnector` inherits `TCPConnector` and has two additional parameters:
* `proxy_link` - used to pass link to proxy server. It can be with credentials in format
`https://username:password@host:port`, or without `https://host:port`. `http` proxies also can be used.
* `proxy_connection_timeout` - used to set wait time for response from proxy server to `CONNECT` request
  (10 seconds by default)
* `insecure_requests` - used to allow connection to proxy server without SSL certificate verification.
  Can be useful when using proxy servers that have no hostname, only ip. In most cases should be ok to use
  default value - `False`
