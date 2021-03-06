import json
import time
from datetime import datetime, timedelta

from api.node_availability_worker import (
    node_availability_batch_size, start_node_availability_worker,
    node_availability_queue
)
from models import (
    db, Node, ProposalAccessPolicy, AVAILABILITY_TIMEOUT, IdentityRegistration,
    NodeAvailability
)
from tests.test_case import TestCase
from tests.utils import (
    build_test_authorization,
    build_static_public_address,
    setting
)
from identity_contract import IdentityContractFake
from api import proposals as proposalEndpoints
from cache import proposalPingCallCache


class TestProposals(TestCase):
    def test_register_proposal_successful(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node = Node.query.get([public_address, "openvpn"])
        self.assertEqual(self.REMOTE_ADDR, node.ip)

    def test_register_proposal_saves_access_policy(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
                "access_policies": [
                    {
                        "id": "test policy",
                        "source": "http://trust-oracle/test-policy"
                    }
                ]
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        policy = ProposalAccessPolicy.query.get([
            public_address,
            "test policy",
            "http://trust-oracle/test-policy"
        ])
        self.assertIsNotNone(policy)

    def test_register_proposal_with_access_policy_succeeds_twice(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
                "access_policies": [
                    {
                        "id": "test policy",
                        "source": "http://trust-oracle/test-policy"
                    }
                ]
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)

        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])

        self.assertEqual(200, re.status_code)

    def test_register_proposal_with_and_without_access_policy(self):
        public_address = build_static_public_address()
        payload1 = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
                "access_policies": [
                    {
                        "id": "test policy",
                        "source": "http://trust-oracle/test-policy"
                    }
                ]
            }
        }
        auth1 = build_test_authorization(json.dumps(payload1))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload1,
            headers=auth1['headers'])
        self.assertEqual(200, re.status_code)

        payload2 = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn"
            }
        }
        auth2 = build_test_authorization(json.dumps(payload2))
        re = self._post(
            '/v1/register_proposal',
            payload2,
            headers=auth2['headers'])

        self.assertEqual(200, re.status_code)

        policy = ProposalAccessPolicy.query.get([
            public_address,
            "test policy",
            "http://trust-oracle/test-policy"
        ])
        self.assertIsNone(policy)

    def test_register_proposal_with_different_access_policies(self):
        public_address = build_static_public_address()
        payload1 = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
                "access_policies": [
                    {
                        "id": "test policy 1",
                        "source": "http://trust-oracle/test-policy-1"
                    }
                ]
            }
        }
        auth1 = build_test_authorization(json.dumps(payload1))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload1,
            headers=auth1['headers'])
        self.assertEqual(200, re.status_code)

        payload2 = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
                "access_policies": [
                    {
                        "id": "test policy 2",
                        "source": "http://trust-oracle/test-policy-2"
                    }
                ]
            }
        }
        auth2 = build_test_authorization(json.dumps(payload2))
        re = self._post(
            '/v1/register_proposal',
            payload2,
            headers=auth2['headers'])

        self.assertEqual(200, re.status_code)

        policy2 = ProposalAccessPolicy.query.get([
            public_address,
            "test policy 2",
            "http://trust-oracle/test-policy-2"
        ])
        self.assertIsNotNone(policy2)

        policy1 = ProposalAccessPolicy.query.get([
            public_address,
            "test policy 1",
            "http://trust-oracle/test-policy-1"
        ])
        self.assertIsNone(policy1)

    def test_register_multiple_proposals_successful(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "dummy",
            }
        }

        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node_openvpn = Node.query.get([public_address, "openvpn"])
        self.assertIsNotNone(node_openvpn)

        node_dummy = Node.query.get([public_address, "dummy"])
        self.assertIsNotNone(node_dummy)

    def test_register_proposal_successful_with_dummy_type(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "dummy",
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node = Node.query.get([public_address, "dummy"])
        self.assertEqual(self.REMOTE_ADDR, node.ip)
        self.assertEqual("dummy", node.service_type)

    def test_register_proposal_successful_with_node_type(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "dummy",
                "service_definition": {
                    "location": {
                        "node_type": "dummy_type"
                    }
                }
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node = Node.query.get([public_address, "dummy"])
        self.assertEqual(self.REMOTE_ADDR, node.ip)
        self.assertEqual("dummy_type", node.node_type)

    def test_register_proposal_successful_with_invalid_definition(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "dummy",
                "service_definition": "test"
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node = Node.query.get([public_address, "dummy"])
        self.assertEqual(self.REMOTE_ADDR, node.ip)
        self.assertEqual('data-center', node.node_type)

    def test_register_proposal_with_unknown_ip(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
            }
        }

        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'],
            remote_addr='127.0.0.1'
        )
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        node = Node.query.get([public_address, "openvpn"])
        self.assertEqual('127.0.0.1', node.ip)

    def test_register_proposal_unauthorized(self):
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": "incorrect",
                "service_type": "openvpn",
            }
        }

        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(403, re.status_code)
        self.assertEqual(
            {'error': 'provider_id does not match current identity'},
            re.json
        )
        self.assertIsNotNone(re.json)

    def test_register_proposal_missing_service_type(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(400, re.status_code)
        self.assertEqual(
            {'error': 'missing service_type'},
            re.json
        )
        self.assertIsNotNone(re.json)

    def test_register_proposal_missing_provider_id(self):
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "service_type": "openvpn",
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(400, re.status_code)
        self.assertEqual(
            {'error': 'missing provider_id'},
            re.json
        )
        self.assertIsNotNone(re.json)

    def test_register_proposal_with_invalid_json(self):
        re = self.client.post('/v1/register_proposal', data='{asd}')
        self.assertEqual(400, re.status_code)
        self.assertEqual({"error": 'payload must be a valid json'}, re.json)

    def test_register_proposal_with_string_json(self):
        # string is actually a valid json,
        # but endpoints rely on json being a dictionary
        re = self.client.post('/v1/register_proposal', data='"some string"')
        self.assertEqual(400, re.status_code)
        self.assertEqual({"error": 'payload must be a valid json'}, re.json)

    def test_register_proposal_with_array_json(self):
        # string is actually a valid json,
        # but endpoints rely on json being a dictionary
        re = self.client.post('/v1/register_proposal', data='[]')
        self.assertEqual(400, re.status_code)
        self.assertEqual({"error": 'payload must be a valid json'}, re.json)

    def test_register_proposal_with_unregistered_identity(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
            }
        }
        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(False)
        re = self._post(
            '/v1/register_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(403, re.status_code)
        self.assertEqual(
            {'error': 'identity is not registered'},
            re.json
        )

    def test_register_proposal_with_verification_disabled(self):
        public_address = build_static_public_address()
        payload = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
            }
        }

        auth = build_test_authorization(json.dumps(payload))
        proposalEndpoints.identity_contract = IdentityContractFake(False)
        with setting('DISCOVERY_VERIFY_IDENTITY', False):
            re = self._post(
                '/v1/register_proposal',
                payload,
                headers=auth['headers'])

        self.assertEqual(200, re.status_code)
        self.assertEqual(
            {},
            re.json
        )

    def test_unregister_proposal_successful(self):
        public_address = build_static_public_address()
        node = self._create_node(public_address, "openvpn")
        node.mark_activity()
        self.assertTrue(node.is_active())

        # unregister
        payload = {
            "provider_id": public_address
        }
        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/unregister_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        self.assertFalse(node.is_active())

    def test_unregister_proposal_multiple_types(self):
        public_address = build_static_public_address()
        node_openvpn = self._create_node(public_address, "openvpn")
        node_openvpn.mark_activity()
        self.assertTrue(node_openvpn.is_active())

        node_dummy = self._create_node(public_address, "dummy")
        node_dummy.mark_activity()
        self.assertTrue(node_dummy.is_active())

        # unregister
        payload = {
            "provider_id": public_address,
            "service_type": "dummy",
        }
        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/unregister_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(200, re.status_code)
        self.assertIsNotNone(re.json)

        self.assertTrue(node_openvpn.is_active())
        self.assertFalse(node_dummy.is_active())

    def test_unregister_proposal_missing_provider(self):
        # unregister
        payload = {

        }
        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/unregister_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(400, re.status_code)
        self.assertEqual({"error": 'missing provider_id'}, re.json)

    def test_unregister_proposal_unauthorized(self):
        payload = {
            "provider_id": "incorrect"
        }

        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/unregister_proposal',
            payload,
            headers=auth['headers'])
        self.assertEqual(403, re.status_code)
        self.assertIsNotNone(re.json)
        self.assertEqual(
            {'error': 'provider_id does not match current identity'},
            re.json
        )

    def test_proposals(self):
        node1 = self._create_node("node1", "openvpn")
        node1.mark_activity()

        # node.updated_at == None
        self._create_node("node2", "openvpn")

        #  node.updated_at timeout passed
        node3 = self._create_node("node3", "openvpn")
        timeout_delta = AVAILABILITY_TIMEOUT + timedelta(minutes=1)
        node3.updated_at = datetime.utcnow() - timeout_delta

        db.session.commit()

        re = self._get('/v1/proposals')
        self.assertEqual(200, re.status_code)
        data = re.json
        proposals = data['proposals']
        self.assertEqual(1, len(proposals))
        self.assertIn('node1', proposals[0]['provider_id'])

    def test_proposals_filtering(self):
        node = self._create_sample_node()
        node.mark_activity()
        db.session.commit()

        re = self._get('/v1/proposals', {'node_key': 'node1'})

        self.assertEqual(200, re.status_code)

        data = json.loads(re.data)
        proposals = data['proposals']
        self.assertEqual(1, len(proposals))
        proposal = proposals[0]
        self.assertIsNotNone(proposal['id'])
        self.assertEqual('node1', proposal['provider_id'])

    def test_proposals_all(self):
        node = self._create_sample_node()
        node.mark_activity()
        node_noop = self._create_node("node2", "noop")
        node_noop.mark_activity()
        db.session.commit()

        re = self._get('/v1/proposals', {'service_type': 'all'})

        self.assertEqual(200, re.status_code)

        data = json.loads(re.data)
        proposals = data['proposals']
        self.assertEqual(2, len(proposals))

    def test_proposals_filtering_service_type_openvpn(self):
        node = self._create_sample_node()
        node.mark_activity()
        db.session.commit()

        re = self._get('/v1/proposals', {'service_type': 'openvpn'})

        self.assertEqual(200, re.status_code)

        data = json.loads(re.data)
        proposals = data['proposals']
        self.assertEqual(1, len(proposals))
        proposal = proposals[0]
        self.assertIsNotNone(proposal['id'])
        self.assertEqual('node1', proposal['provider_id'])
        self.assertEqual(node.service_type, "openvpn")

    def test_proposals_filtering_service_type_string(self):
        node = self._create_sample_node()
        node.mark_activity()
        db.session.commit()

        re = self._get(
            '/v1/proposals',
            {'service_type': 'something else entirely'}
        )

        self.assertEqual(200, re.status_code)

        data = json.loads(re.data)
        proposals = data['proposals']
        self.assertEqual(0, len(proposals))

    def test_proposals_filtering_no_service_type(self):
        node = self._create_sample_node()
        node.mark_activity()
        db.session.commit()

        re = self._get(
            '/v1/proposals'
        )

        self.assertEqual(200, re.status_code)

        data = json.loads(re.data)
        proposals = data['proposals']
        self.assertEqual(1, len(proposals))
        proposal = proposals[0]
        self.assertIsNotNone(proposal['id'])
        self.assertEqual('node1', proposal['provider_id'])
        self.assertEqual(node.service_type, "openvpn")

    def test_proposals_with_unknown_node_key(self):
        self._create_sample_node()

        re = self._get('/v1/proposals', {'node_key': 'UNKNOWN'})

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual([], data['proposals'])

    def test_proposals_returns_all_proposals_without_policies(self):
        n1 = self._create_node("node1", "openvpn")
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn", "mysterium", "test source")
        n2.mark_activity()

        re = self._get(
            '/v1/proposals',
            {'service_type': 'all'}
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(1, len(data['proposals']))
        self.assertEqual('node1', data['proposals'][0]['provider_id'])

    def test_proposals_filtering_by_access_policy(self):
        n1 = self._create_node("node1", "openvpn")
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn", "mysterium", "test source")
        n2.mark_activity()
        n3 = self._create_node("node3", "openvpn", "private", "test source")
        n3.mark_activity()

        re = self._get(
            '/v1/proposals',
            {
                'service_type': 'all',
                'access_policy[id]': 'mysterium',
                'access_policy[source]': 'test source',
            }
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(1, len(data['proposals']))
        self.assertEqual('node2', data['proposals'][0]['provider_id'])

    def test_proposals_filtering_by_access_policy_single_param(self):
        n1 = self._create_node("node1", "openvpn")
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn", "mysterium", "test source")
        n2.mark_activity()

        re = self._get(
            '/v1/proposals',
            {
                'service_type': 'all',
                'access_policy[id]': 'mysterium'
            }
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(1, len(data['proposals']))
        self.assertEqual('node2', data['proposals'][0]['provider_id'])

    def test_proposals_filtering_bounty_only(self):
        n1 = self._create_node("node1", "openvpn")
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn")
        n2.mark_activity()

        self._create_identity_registration("node2", "some_address")

        re = self._get(
            '/v1/proposals',
            {
                'service_type': 'all',
                'bounty_only': 'true',
            }
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(1, len(data['proposals']))
        self.assertEqual('node2', data['proposals'][0]['provider_id'])

    def test_proposals_filtering_by_star_policy_returns_all_proposals(self):
        n1 = self._create_node("node1", "openvpn")
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn", "mysterium", "test source")
        n2.mark_activity()

        re = self._get(
            '/v1/proposals',
            {'service_type': 'all', 'access_policy': '*'}
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(2, len(data['proposals']))

    def test_proposals_filtering_by_node_type(self):
        n1 = self._create_node("node1", "openvpn")
        n1.node_type = "dummy_type"
        n1.mark_activity()
        n2 = self._create_node("node2", "openvpn", "mysterium", "test source")
        n2.mark_activity()

        re = self._get(
            '/v1/proposals',
            {'node_type': 'dummy_type'}
        )

        self.assertEqual(200, re.status_code)
        data = json.loads(re.data)
        self.assertEqual(1, len(data['proposals']))

    def test_ping_proposal_with_service_type(self):
        start_node_availability_worker(db.engine, node_availability_queue)

        payload = {'service_type': 'dummy_service'}
        auth = build_test_authorization(json.dumps(payload))

        self._create_node(auth['public_address'], "dummy_service")

        re = Node
        for i in range(node_availability_batch_size):
            re = self._post(
                '/v1/ping_proposal',
                payload,
                headers=auth['headers']
            )
            self.assertEqual(200, re.status_code)

        # Sleep for some time to wait for inserted availabilities.
        time.sleep(3)

        # Detach current session so NodeAvailability model can pick new changes inserted from another session.
        db.session.remove()
        pings = NodeAvailability.query.filter(
            getattr(NodeAvailability, 'service_type') == payload['service_type']
        ).all()

        self.assertEqual({}, re.json)
        self.assertEqual(pings[0].service_type, "dummy_service")

    def test_ping_proposal_no_node_with_service_type(self):
        payload = {'service_type': 'dummy'}
        auth = build_test_authorization(json.dumps(payload))

        self._create_node(auth['public_address'], "openvpn")

        re = self._post(
            '/v1/ping_proposal',
            payload,
            headers=auth['headers']
        )
        self.assertEqual(400, re.status_code)
        self.assertEqual({'error': 'node key not found'}, re.json)

    def test_ping_proposal_with_type(self):
        payload = {}
        auth = build_test_authorization(json.dumps(payload))

        node = self._create_node(auth['public_address'], "dummy")

        re = self._post(
            '/v1/ping_proposal',
            payload,
            headers=auth['headers']
        )
        self.assertEqual(400, re.status_code)
        self.assertEqual({'error': 'node key not found'}, re.json)

        payload = {'service_type': 'dummy'}
        auth = build_test_authorization(json.dumps(payload))
        re = self._post(
            '/v1/ping_proposal',
            payload,
            headers=auth['headers']
        )
        self.assertEqual(200, re.status_code)
        self.assertEqual({}, re.json)

    def test_node_send_stats_with_unknown_node(self):
        payload = {}
        auth = build_test_authorization(json.dumps(payload))

        re = self._post(
            '/v1/node_send_stats',
            payload,
            headers=auth['headers']
        )
        self.assertEqual(400, re.status_code)
        self.assertEqual({'error': 'node key not found'}, re.json)

    # TODO: DRY
    def _create_sample_node(self):
        return self._create_node("node1", "openvpn")

    # TODO: DRY
    def _create_node(self, node_key, service_type, access_policy_id=None,
                     access_policy_source=None):
        node = Node(node_key, service_type)
        node.proposal = json.dumps({
            "id": 1,
            "format": "service-proposal/v1",
            "provider_id": node_key,
        })
        db.session.add(node)

        if access_policy_id and access_policy_source:
            item = ProposalAccessPolicy(node_key, access_policy_id,
                                        access_policy_source)
            db.session.add(item)

        return node

    def _create_identity_registration(self, node_key, eth_address):
        ir = IdentityRegistration(node_key, eth_address)
        db.session.add(ir)
        return ir

    def test_proposal_rate_limited_ping(self):
        payload_openvpn = {'service_type': 'openvpn'}
        auth_openvpn = build_test_authorization(json.dumps(payload_openvpn))
        payload_wireguard = {'service_type': 'wireguard'}
        auth_wireguard = build_test_authorization(json.dumps(payload_wireguard))
        proposalPingCallCache.clear()
        self._create_node(auth_openvpn['public_address'], "openvpn")
        self._create_node(auth_wireguard['public_address'], "wireguard")
        with setting('THROTTLE_PROPOSAL_PING', True):
            re = self._post(
                '/v1/ping_proposal',
                payload_openvpn,
                headers=auth_openvpn['headers']
            )
            self.assertEqual(200, re.status_code)
            self.assertEqual({}, re.json)
            re = self._post(
                '/v1/ping_proposal',
                payload_openvpn,
                headers=auth_openvpn['headers']
            )
            self.assertEqual(429, re.status_code)
            self.assertEqual({'error': 'too many requests'}, re.json)
            re = self._post(
                '/v1/ping_proposal',
                payload_wireguard,
                headers=auth_wireguard['headers']
            )
            self.assertEqual(200, re.status_code)
            re = self._post(
                '/v1/ping_proposal',
                payload_wireguard,
                headers=auth_wireguard['headers']
            )
            self.assertEqual(429, re.status_code)
            self.assertEqual({'error': 'too many requests'}, re.json)

    def test_proposal_rate_limited_register(self):
        public_address = build_static_public_address()
        payload_openvpn = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "openvpn",
            }
        }
        auth_openvpn = build_test_authorization(json.dumps(payload_openvpn))
        payload_wireguard = {
            "service_proposal": {
                "id": 1,
                "format": "service-proposal/v1",
                "provider_id": public_address,
                "service_type": "wireguard",
            }
        }
        auth_wireguard = build_test_authorization(json.dumps(payload_wireguard))
        proposalEndpoints.identity_contract = IdentityContractFake(True)
        proposalPingCallCache.clear()
        with setting('THROTTLE_PROPOSAL_PING', True):
            re = self._post(
                '/v1/register_proposal',
                payload_openvpn,
                headers=auth_openvpn['headers'])
            self.assertEqual(200, re.status_code)
            self.assertIsNotNone(re.json)
            re = self._post(
                '/v1/register_proposal',
                payload_openvpn,
                headers=auth_openvpn['headers'])
            self.assertEqual(429, re.status_code)
            self.assertEqual({'error': 'too many requests'}, re.json)

            re = self._post(
                '/v1/register_proposal',
                payload_wireguard,
                headers=auth_wireguard['headers'])
            self.assertEqual(200, re.status_code)
            self.assertIsNotNone(re.json)
            re = self._post(
                '/v1/register_proposal',
                payload_wireguard,
                headers=auth_wireguard['headers'])
            self.assertEqual(429, re.status_code)
            self.assertEqual({'error': 'too many requests'}, re.json)
