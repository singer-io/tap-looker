from datetime import datetime, timedelta
import backoff
import requests
import singer
from singer import metrics

LOGGER = singer.get_logger()

API_DOMAIN_DEFAULT = 'looker.com'
API_PORT_DEFAULT = '19999'
API_VERSIONS_SUPPORTED = ['2.99', '3.0', '3.1']
API_VERSION_DEFAULT = '3.1'


class Server5xxError(Exception):
    pass

class Server429Error(Exception):
    pass

class LookerClient:

    # pylint: disable=too-many-instance-attributes
    def __init__(self,
                 subdomain,
                 client_id,
                 client_secret,
                 domain=None,
                 api_port=None,
                 api_version=None,
                 user_agent=None):
        self.__subdomain = subdomain
        self.__client_id = client_id
        self.__client_secret = client_secret

        if domain:
            self.__domain = domain
        else:
            self.__domain = API_DOMAIN_DEFAULT
        if api_version in API_VERSIONS_SUPPORTED:
            self.__api_version = api_version
        else:
            self.__api_version = API_VERSION_DEFAULT
        if api_port:
            self.__api_port = api_port
        else:
            self.__api_port = API_PORT_DEFAULT
        if user_agent:
            self.__user_agent = user_agent
        else:
            self.__user_agent = 'tap-looker ({}.{})'.format(
                self.__subdomain, self.__domain)
        self.__access_token = None
        self.__expires = None
        self.__session = requests.Session()
        self.base_url = 'https://{}.{}:{}/api/{}'.format(
            self.__subdomain,
            self.__domain,
            self.__api_port,
            self.__api_version
        )

    def __enter__(self):
        self.get_access_token()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.__session.close()

    # API Authentication:
    #  https://docs.looker.com/reference/api-and-integration/api-reference/v3.1/api-auth
    @backoff.on_exception(backoff.expo,
                          Server5xxError,
                          max_tries=5,
                          factor=2)
    def get_access_token(self):
        if self.__access_token is not None and self.__expires > datetime.utcnow():
            return

        headers = {}
        headers['User-Agent'] = self.__user_agent
        headers['Accept'] = 'application/json'

        response = self.__session.post(
            url='{}/login'.format(self.base_url),
            headers=headers,
            data={'client_id': self.__client_id,
                  'client_secret': self.__client_secret})

        if response.status_code >= 500:
            raise Server5xxError()

        if response.status_code != 200:
            looker_response = response.json()
            looker_response.update(
                {'status': response.status_code})
            raise Exception(
                'Unable to authenticate (Looker response: `{}`)'.format(
                    looker_response))

        data = response.json()
        self.__access_token = data['access_token']
        expires_seconds = data['expires_in'] - 60 # pad by 60 seconds
        self.__expires = datetime.utcnow() + timedelta(seconds=expires_seconds)


    @backoff.on_exception(backoff.expo,
                          (Server5xxError, ConnectionError, Server429Error),
                          max_tries=7,
                          factor=3)
    # @utils.ratelimit(400, 60)
    def request(self, method, path=None, url=None, json=None, **kwargs):
        self.get_access_token()

        if not url and path:
            url = '{}/{}'.format(self.base_url, path)

        if 'endpoint' in kwargs:
            endpoint = kwargs['endpoint']
            del kwargs['endpoint']
        else:
            endpoint = None

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Authorization'] = 'Bearer {}'.format(self.__access_token)
        kwargs['headers']['User-Agent'] = self.__user_agent
        kwargs['headers']['Accept'] = 'application/json'

        if method == 'POST':
            kwargs['headers']['Content-Type'] = 'application/json'

        with metrics.http_request_timer(endpoint) as timer:
            response = self.__session.request(
                method=method,
                url=url,
                json=json,
                **kwargs)
            timer.tags[metrics.Tag.http_status_code] = response.status_code

        status_code = response.status_code
        LOGGER.info('status_code = %s', status_code)

        if status_code >= 500:
            raise Server5xxError()

        #Use retry functionality in backoff to wait and retry if
        #response code equals 429 because rate limit has been exceeded
        elif status_code == 429:
            raise Server429Error()

        elif status_code == 404:
            if endpoint in ('explores', 'models', 'merge_queries', 'queries'):
                LOGGER.warning('HTTP 404 Error, URL Not Found: %s', url)
                return None
            else:
                response.raise_for_status()

        elif status_code == 200:
            return response.json()

        response.raise_for_status()
