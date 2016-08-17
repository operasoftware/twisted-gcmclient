import json
import logging

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import HTTPConnectionPool

import treq

DEFAULT_SEND_URL = 'https://android.googleapis.com/gcm/send'

logger = logging.getLogger(__name__)
pool = HTTPConnectionPool(reactor)


class GCMClientError(Exception):
    pass


class GCMClientBadRequestError(GCMClientError):
    pass


class GCMClientAuthenticationError(GCMClientError):
    pass


class GCMClientInternalServerError(GCMClientError):

    def __init__(self, code=None):
        message = 'GCM internal server error: %s' % code
        super(GCMClientInternalServerError, self).__init__(message)


class GCMClientInvalidRegistrationError(GCMClientError):
    pass


class GCMClientInvalidParametersError(GCMClientError):
    pass


class GCMClientNotRegisteredError(GCMClientError):
    pass


class GCMClientMessageTooBig(GCMClientError):
    pass


class GCMClientUnknownHTTPError(GCMClientError):
    pass


class GCMClientUnknownCodeError(GCMClientError):
    pass


class GCMClientDeviceMessageRateExceeded(GCMClientError):
    pass


class GCMClientReplaceRegistrationId(GCMClientError):

    def __init__(self, registration_id):
        super(GCMClientReplaceRegistrationId, self).__init__()
        self.registration_id = registration_id


class GCMClientMismatchSenderIdError(GCMClientError):
    pass


class GCMClient(object):
    """
    Google Cloud Messaging (GCM) HTTP client. Based on
    http://developer.android.com/google/gcm/http.html.

    TODO support for Send-to-Sync messages -
         http://developer.android.com/google/gcm/server.html#s2s
    TODO support for time to live (TTL)
    TODO handle 'Invalid Package Name' error
    TODO handle 'Timeout' error
    """

    CODE_TO_ERROR = {
        'DeviceMessageRateExceeded': GCMClientDeviceMessageRateExceeded,
        'InternalServerError': GCMClientInternalServerError,
        'InvalidRegistration': GCMClientInvalidRegistrationError,
        'InvalidParameters': GCMClientInvalidParametersError,
        'MessageTooBig': GCMClientMessageTooBig,
        'MismatchSenderId': GCMClientMismatchSenderIdError,
        'NotRegistered': GCMClientNotRegisteredError
    }

    def __init__(self, api_key, url=DEFAULT_SEND_URL):
        self.api_key = api_key
        self.url = url

    @inlineCallbacks
    def send(
            self, registration_id, message, dry_run=False, custom_headers=None):
        payload = {
            'registration_ids': [registration_id],
            'data': message,
        }

        if dry_run:
            payload['dry_run'] = True

        headers = {
            'Authorization': 'key=%s' % self.api_key,
            'Content-Type': 'application/json'
        }

        if custom_headers is not None:
            headers.update(custom_headers)

        resp = yield treq.post(
            self.url, data=json.dumps(payload), headers=headers, pool=pool)

        # Response handling based on:
        # * http://developer.android.com/google/gcm/http.html#response
        # * http://developer.android.com/google/gcm/server-ref.html#error-codes

        if resp.code == 200:
            content = yield resp.json()

            if content['failure'] == 0 and content['canonical_ids'] == 0:
                return

            result = content['results'][0]

            if 'message_id' in result and 'registration_id' in result:
                raise GCMClientReplaceRegistrationId(result['registration_id'])

            code = result['error']
            error = self.CODE_TO_ERROR.get(code)

            if error is None:
                raise GCMClientUnknownCodeError(code)
            else:
                raise error()
        elif resp.code == 400:
            content = yield resp.text()
            raise GCMClientBadRequestError(content)
        elif resp.code == 401:
            raise GCMClientAuthenticationError()
        elif 500 <= resp.code < 600:
            retry_after = resp.headers.getRawHeaders('Retry-After', [None])[0]
            if retry_after is not None:
                logger.error(
                    'GCM response with Retry-After header',
                    extra={'retry_after': retry_after})
            raise GCMClientInternalServerError(resp.code)
        else:
            raise GCMClientUnknownHTTPError(resp.code)
