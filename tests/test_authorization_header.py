import unittest
from tests.test_case import TestCase
from request_helpers import decode_authorization_header
import base64
from tests.utils import (
    sign_message_with_static_key,
    build_static_public_address,
)


class TestAuthorizationHeader(TestCase):
    def test_incorrect_authorization_header(self):
        headers = {
            "incorrectAuthorizationHeader": "Signature sig"
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual(
            'missing Authorization in request header',
            str(err.exception)
        )

    def test_incorrect_authorization_header_value_format(self):
        headers = {
            "Authorization": "Signature"
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual(
            'invalid Authorization header value provided, correct'
            ' format: Signature <signature_base64_encoded>',
            str(err.exception)
        )

    def test_incorrect_authorization_type(self):
        headers = {
            "Authorization": "incorrectType sig"
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual(
            'authentication type have to be Signature',
            str(err.exception)
        )

    def test_empty_authorization_header_value(self):
        headers = {
            "Authorization": "Signature "
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual('signature was not provided', str(err.exception))

    def test_signature_not_base64_encoded(self):
        headers = {
            "Authorization": "Signature not_base_64"
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual(
            'signature must be base64 encoded: Incorrect padding',
            str(err.exception)
        )

    def test_incorrect_signature_format(self):
        signature = sign_message_with_static_key('')
        invalid_signature = base64.b64encode(signature+b'1').decode("utf-8")

        headers = {
            "Authorization": "Signature {}".format(invalid_signature)
        }

        with self.assertRaises(ValueError) as err:
            decode_authorization_header(headers)
        self.assertEqual(
            'invalid signature format: Unexpected signature format.'
            '  Must be length 65 byte string',
            str(err.exception)
        )

    def test_successful(self):
        signature = sign_message_with_static_key('')
        public_address = build_static_public_address()

        signature_value = base64.b64encode(signature).decode("utf-8")
        headers = {
            "Authorization": "Signature {}".format(signature_value)
        }

        recovered_public_address = decode_authorization_header(headers)
        self.assertEqual(public_address.lower(), recovered_public_address)


if __name__ == '__main__':
    unittest.main()
