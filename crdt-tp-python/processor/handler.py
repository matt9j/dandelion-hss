# Copyright 2016 Intel Corporation
# Copyright 2018 University of Washington
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import logging

import cbor
import enum
import hashlib

from sawtooth_sdk.processor.exceptions import InternalError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.handler import TransactionHandler


FAMILY_METADATA = {
    'name': 'billing-crdt',
    'versions': ['0.0.1'],
    }

FAMILY_METADATA['prefixes'] = [
    hashlib.sha512(FAMILY_METADATA['name'].encode('utf-8')).hexdigest()[0:6],
    ]

_CHAIN_STRUCTURE_ADDRESS_MAX_LENGTH = 60


class ChainStructureTag(enum.Enum):
    """Tags following the transaction family prefix for different chain structures"""
    USERS = '0000'
    NETWORKS = '0001'
    CRDT = '0002'


class ActionTypes(enum.Enum):
    """The types of messages available for processing"""
    ADD_USER = 0
    ADD_NET = 1
    SPEND = 2
    TOP_UP = 3


LOGGER = logging.getLogger(__name__)


def make_crdt_address(name):
    return FAMILY_METADATA['prefixes'][0] + hashlib.sha512(
        name.encode('utf-8')).hexdigest()[-64:]


def make_user_address(user_id):
    # TODO(matt9j) Clean up user id handling and separate from IMSI
    # Check if the user_id is a valid hex string
    try:
        int(user_id, 16)
    except ValueError:
        raise ValueError('The UserId \'{}\' is not a valid hex string'.format(user_id))

    if len(user_id) > _CHAIN_STRUCTURE_ADDRESS_MAX_LENGTH:
        raise ValueError('The UserId must be at most {} hex characters \'{}\' is {} characters'.format(
                _CHAIN_STRUCTURE_ADDRESS_MAX_LENGTH, user_id, len(user_id)))
    # Pad the user id out to the max length
    padded_id = user_id.rjust(_CHAIN_STRUCTURE_ADDRESS_MAX_LENGTH, '0')

    return FAMILY_METADATA['prefixes'][0] + ChainStructureTag.USERS.value + padded_id


class CrdtTransactionHandler(TransactionHandler):
    @property
    def family_name(self):
        return FAMILY_METADATA['name']

    @property
    def family_versions(self):
        return FAMILY_METADATA['versions']

    @property
    def namespaces(self):
        return FAMILY_METADATA['prefixes']

    def apply(self, transaction, context):
        action, action_payload = _unpack_transaction(transaction)

        _do_action(action, action_payload, context)

        state = _get_state_data(name, context)

        updated_state = _do_intkey(verb, name, value, state)

        _set_state_data(name, updated_state, context)


def _unpack_transaction(transaction):
    action, action_payload = _decode_action(transaction)

    _validate_action(action)

    return action, action_payload


def _decode_action(transaction):
    try:
        content = cbor.loads(transaction.payload)
    except:
        raise InvalidTransaction('Invalid payload serialization')

    try:
        action_string = content['action']
        action = ActionTypes(action_string)
    except (AttributeError, ValueError):
        raise InvalidTransaction('action is required')

    try:
        action_payload = content['payload']
    except AttributeError:
        raise InvalidTransaction('action payload is required')

    return action, action_payload


def _validate_action(action):
    if action not in ActionTypes:
        raise InvalidTransaction('Action must be in' + str(ActionTypes))


def _do_action(action, action_payload, context):
    if action == ActionTypes.ADD_USER:
        _add_user(action_payload, context)
    elif action == ActionTypes.ADD_NET:
        raise NotImplementedError("The action" + str(action) + " is not supported yet.")
    elif action == ActionTypes.SPEND:
        raise NotImplementedError("The action" + str(action) + " is not supported yet.")
    elif action == ActionTypes.TOP_UP:
        raise NotImplementedError("The action" + str(action) + " is not supported yet.")
    else:
        raise NotImplementedError("The action" + str(action) + " is not supported yet.")


def _add_user(serialized_payload, context):
    imsi, pub_key, home_network = _parse_add_user(serialized_payload)
    # TODO(matt9j) Validate the user signature against the public key!
    # TODO(matt9j) Validate the network signature against the known home network key!

    address = make_user_address(imsi)
    try:
        _get_state_data(address, context)
        raise InvalidTransaction('The user {} already exists'.format(imsi))
    except IndexError:
        # It's okay if the user does not exist.
        pass

    user_state = {'id': imsi, 'pub_key': pub_key, 'home_net': home_network}
    _set_state_data(address, user_state, context)


def _parse_add_user(serialized_payload):
    """Deserialize the add user payload"""
    try:
        payload = cbor.loads(serialized_payload)
    except:
        raise InvalidTransaction('Invalid user add payload serialization')

    try:
        imsi = payload['imsi']
    except AttributeError:
        raise InvalidTransaction('The new user imsi is required')

    try:
        pub_key = payload['pub_key']
    except AttributeError:
        raise InvalidTransaction('The new user public key is required')

    try:
        home_network = payload['home_net']
    except AttributeError:
        raise InvalidTransaction('The new user home network is required')

    return imsi, pub_key, home_network


def _get_state_data(address, context):
    state_entries = context.get_state([address])

    try:
        return cbor.loads(state_entries[0].data)
    except IndexError:
        return {}


def _set_state_data(address, state, context):
    encoded = cbor.dumps(state)

    addresses = context.set_state({address: encoded})

    if not addresses:
        raise InternalError('State error')
