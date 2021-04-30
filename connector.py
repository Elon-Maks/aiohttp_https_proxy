import ssl
import asyncio
from aiohttp import TCPConnector
from urllib.parse import urlparse
import base64
from yarl import URL
import re
from urllib.parse import unquote
import time


def parse_response(response_text):
    response_text = response_text.decode()
    status = re.search('HTTP/\d\.\d (\d+)', response_text)[1]
    message = re.search('HTTP/\d\.\d \d+ ([\w ]+)\r', response_text)[1]
    return int(status), message


class HTTPSProxyConnector(TCPConnector):
    def __init__(
        self,
        proxy_link,
        proxy_connection_timeout = 10,
        **kwargs
    ):
        super().__init__(**kwargs)
        parsed_link = urlparse(proxy_link)
        self._proxy_link = proxy_link
        self._proxy_type = parsed_link.scheme
        self._proxy_host = parsed_link.hostname
        self._proxy_username = unquote(parsed_link.username) if parsed_link.username else None
        self._proxy_password = unquote(parsed_link.password) if parsed_link.password else None
        self._proxy_connection_timeout = proxy_connection_timeout
        if parsed_link.username and parsed_link.password:
            self._proxy_auth = 'Basic ' + (base64.standard_b64encode(f'{self._proxy_username}:'
                                                                     f'{self._proxy_password}'.encode('latin1')
                                                                     ).decode('latin1'))
        else:
            self._proxy_auth = None
        self._proxy_port = parsed_link.port
        try:
            import uvloop
            if not isinstance(asyncio.get_running_loop(), uvloop.Loop):
                raise Exception('This connector only works with uvloop')
        except ImportError:
            raise Exception('uvloop is required to use this connector')


    @property
    def proxy_url(self):
        if self._proxy_username:
            url_tpl = "{scheme}://{username}:{password}@{host}:{port}"
        else:
            url_tpl = "{scheme}://{host}:{port}"

        url = url_tpl.format(
            scheme=self._proxy_type,
            username=self._proxy_username,
            password=self._proxy_password,
            host=self._proxy_host,
            port=self._proxy_port,
        )
        return URL(url)

    async def _wrap_create_connection(
        self, protocol_factory, host=None, port=None, *args, **kwargs
    ):
        if self._proxy_type == 'https':
            loop = asyncio.get_running_loop()
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            if self._proxy_auth:
                kwargs['req'].headers['Proxy-Authorization'] = self._proxy_auth
            transport, protocol = await loop.create_connection(protocol_factory,
                                                               host=self._proxy_host,
                                                               port=self._proxy_port,
                                                               ssl=True)
            if kwargs.get('ssl'):
                query = f'CONNECT {host}:{port} HTTP/1.1\r\n'
                if self._proxy_auth:
                    query += f'Host: {self._proxy_host}\r\nProxy-Authorization: {self._proxy_auth}\r\n'
                query += '\r\n'
                transport.write(query.encode('latin1'))
                timer = time.time()
                while protocol._tail == b'':
                    await asyncio.sleep(0.01)
                    if time.time() - timer > self._proxy_connection_timeout:
                        raise Exception('Proxy connection connection timeout: answer not received')
                status, message = parse_response(protocol._tail)
                if status != 200:
                    raise Exception(f'Proxy connection error: {status} "{message}"')
                transport = await loop.start_tls(transport, protocol, context)
                protocol._tail = b''
                protocol.transport = transport
            return transport, protocol
        else:
            return await super(HTTPSProxyConnector, self)._wrap_create_connection(
                protocol_factory, host, port, *args, **kwargs
            )

    async def connect(self, req, traces, timeout):
        if self._proxy_type == 'http':
            req.update_proxy(
                self.proxy_url, None, req.proxy_headers
            )
        return await super(HTTPSProxyConnector, self).connect(
            req=req, traces=traces, timeout=timeout
        )
