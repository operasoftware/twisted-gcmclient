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
    GCMClientUnknownHTTPError,
    pool
)


class GCMClientTestCase(unittest.TestCase):

    @patch('gcmclient.treq.post')
    def test_200(self, post_mock):
        api_key = '123456789'
        client = GCMClient(api_key)
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        post_mock.return_value = response

        client.send(registration_id, message)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message})
        headers = {'Authorization': 'key=' + api_key,
                   'Content-Type': 'application/json'}
        post_mock.assert_called_once_with(
            client.url, data=data, headers=headers, pool=pool)

    @patch('gcmclient.treq.post')
    def test_200_custom_headers(self, post_mock):
        api_key = '123456789'
        client = GCMClient(api_key)
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        post_mock.return_value = response

        custom_headers = {'Header': 'Value'}
        client.send(registration_id, message, custom_headers=custom_headers)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message})
        headers = {'Authorization': 'key=' + api_key,
                   'Content-Type': 'application/json'}
        headers.update(custom_headers)

        post_mock.assert_called_once_with(
            client.url, data=data, headers=headers, pool=pool)

    @patch('gcmclient.treq.post')
    def test_200_dry_run(self, post_mock):
        api_key = '123456789'
        client = GCMClient(api_key)
        registration_id = 'foo'
        message = 'bar'
        response = Mock(code=200)
        response.json.return_value = {'failure': 0, 'canonical_ids': 0}
        post_mock.return_value = response

        client.send(registration_id, message, dry_run=True)

        data = json.dumps({'registration_ids': [registration_id],
                           'data': message,
                           'dry_run': True})
        headers = {'Authorization': 'key=' + api_key,
                   'Content-Type': 'application/json'}
        post_mock.assert_called_once_with(
            client.url, data=data, headers=headers, pool=pool)

    @patch('gcmclient.treq.post')
    def test_code_to_error_miss(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=200)
        code = 123
        response.json.return_value = {'failure': 1,
                                      'results': [{'error': code}]}
        post_mock.return_value = response

        with patch('gcmclient.GCMClient.CODE_TO_ERROR', {}):
            failure = self.failureResultOf(client.send('foo', 'bar'),
                                           GCMClientUnknownCodeError)
            self.assertEqual(failure.getErrorMessage(), str(code))


    @patch('gcmclient.treq.post')
    def test_code_to_error_hit(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=200)
        code = 123
        response.json.return_value = {'failure': 1,
                                      'results': [{'error': code}]}
        post_mock.return_value = response

        class MyException(Exception):
            pass

        with patch('gcmclient.GCMClient.CODE_TO_ERROR',
                   {code: MyException}):
            self.failureResultOf(client.send('foo', 'bar'), MyException)

    @patch('gcmclient.treq.post')
    def test_replace_registration_id(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=200)
        response.json.return_value = {'failure': 0,
                                      'canonical_ids': 1,
                                      'results': [{'message_id': '1',
                                                   'registration_id': 2}]}
        post_mock.return_value = response

        self.failureResultOf(client.send('foo', 'bar'),
                             GCMClientReplaceRegistrationId)

    @patch('gcmclient.treq.post')
    def test_400(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=400)
        response.text.return_value = 'something went wrong'
        post_mock.return_value = response

        failure = self.failureResultOf(client.send('foo', 'bar'),
                                       GCMClientBadRequestError)
        self.assertEqual(failure.getErrorMessage(), response.text.return_value)

    @patch('gcmclient.treq.post')
    def test_401(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=401)
        post_mock.return_value = response

        self.failureResultOf(client.send('foo', 'bar'),
                             GCMClientAuthenticationError)

    @patch('gcmclient.treq.post')
    def test_500(self, post_mock):
        client = GCMClient('123456789')
        response = MagicMock(code=500)
        post_mock.return_value = response

        self.failureResultOf(client.send('foo', 'bar'),
                             GCMClientInternalServerError)

    @patch('gcmclient.treq.post')
    def test_502(self, post_mock):
        client = GCMClient('123456789')
        response = MagicMock(code=502)
        post_mock.return_value = response

        self.failureResultOf(client.send('foo', 'bar'),
                             GCMClientInternalServerError)

    @patch('gcmclient.treq.post')
    def test_unknown_http_error(self, post_mock):
        client = GCMClient('123456789')
        response = Mock(code=666)
        post_mock.return_value = response

        failure = self.failureResultOf(client.send('foo', 'bar'),
                                       GCMClientUnknownHTTPError)
        self.assertEqual(failure.getErrorMessage(), str(response.code))
