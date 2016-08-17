import json

from mock import patch, Mock, MagicMock

from twisted.trial import unittest

from gcmclient import (
    GCMClient,
    GCMClientAuthenticationError,
    GCMClientBadRequestError,
    GCMClientInternalServerError,
    GCMClientReplaceRegistrationId,
    GCMClientUnknownCodeError,
    GCMClientUnknownHTTPError
)


class GCMClientTestCase(unittest.TestCase):

    def setUp(self):
        self.http_client = Mock()
        self.post_mock = self.http_client.post
        self.api_key = '123456789'
        self.client = GCMClient(self.api_key, http_client=self.http_client)

    def test_200(self):
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        self.post_mock.return_value = response

        self.client.send(registration_id, message)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message})
        headers = {'Authorization': 'key=' + self.api_key,
                   'Content-Type': 'application/json'}
        self.post_mock.assert_called_once_with(
            self.client.url, data=data, headers=headers)

    def test_200_custom_headers(self):
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        self.post_mock.return_value = response

        custom_headers = {'Header': 'Value'}
        self.client.send(registration_id, message, custom_headers=custom_headers)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message})
        headers = {'Authorization': 'key=' + self.api_key,
                   'Content-Type': 'application/json'}
        headers.update(custom_headers)

        self.post_mock.assert_called_once_with(
            self.client.url, data=data, headers=headers)

    def test_200_dry_run(self):
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        self.post_mock.return_value = response

        self.client.send(registration_id, message, dry_run=True)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message,
                           'dry_run': True})
        headers = {'Authorization': 'key=' + self.api_key,
                   'Content-Type': 'application/json'}
        self.post_mock.assert_called_once_with(
            self.client.url, data=data, headers=headers)

    def test_code_to_error_miss(self):
        response = Mock(code=200)
        code = 123
        response.json.return_value = {'failure': 1,
                                      'results': [{'error': code}]}
        self.post_mock.return_value = response

        with patch('gcmclient.GCMClient.CODE_TO_ERROR', {}):
            failure = self.failureResultOf(self.client.send('foo', 'bar'),
                                           GCMClientUnknownCodeError)
            self.assertEqual(failure.getErrorMessage(), str(code))


    def test_code_to_error_hit(self):
        response = Mock(code=200)
        code = 123
        response.json.return_value = {'failure': 1,
                                      'results': [{'error': code}]}
        self.post_mock.return_value = response

        class MyException(Exception):
            pass

        with patch('gcmclient.GCMClient.CODE_TO_ERROR',
                   {code: MyException}):
            self.failureResultOf(self.client.send('foo', 'bar'), MyException)

    def test_replace_registration_id(self):
        response = Mock(code=200)
        response.json.return_value = {'failure': 0,
                                      'canonical_ids': 1,
                                      'results': [{'message_id': '1',
                                                   'registration_id': 2}]}
        self.post_mock.return_value = response

        self.failureResultOf(self.client.send('foo', 'bar'),
                             GCMClientReplaceRegistrationId)

    def test_400(self):
        response = Mock(code=400)
        response.text.return_value = 'something went wrong'
        self.post_mock.return_value = response

        failure = self.failureResultOf(self.client.send('foo', 'bar'),
                                       GCMClientBadRequestError)
        self.assertEqual(failure.getErrorMessage(), response.text.return_value)

    def test_401(self):
        response = Mock(code=401)
        self.post_mock.return_value = response

        self.failureResultOf(self.client.send('foo', 'bar'),
                             GCMClientAuthenticationError)

    def test_500(self):
        response = MagicMock(code=500)
        self.post_mock.return_value = response

        self.failureResultOf(self.client.send('foo', 'bar'),
                             GCMClientInternalServerError)

    def test_502(self):
        response = MagicMock(code=502)
        self.post_mock.return_value = response

        self.failureResultOf(self.client.send('foo', 'bar'),
                             GCMClientInternalServerError)

    def test_unknown_http_error(self):
        response = Mock(code=666)
        self.post_mock.return_value = response

        failure = self.failureResultOf(self.client.send('foo', 'bar'),
                                       GCMClientUnknownHTTPError)
        self.assertEqual(failure.getErrorMessage(), str(response.code))
