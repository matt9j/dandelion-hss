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
import nacl.signing
import nacl.encoding

from sawtooth_sdk.processor.exceptions import InternalError
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.handler import TransactionHandler

from asterales_protocol.definitions import ActionTypes, make_user_address, make_network_address
from asterales_protocol.definitions import FAMILY_METADATA


LOGGER = logging.getLogger(__name__)


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
        try:
            action, action_payload = _unpack_transaction(transaction)

            _do_action(action, action_payload, context)
        # In Sawtooth (at least version 1.0.*) InternalErrors will result in
        # a retry, InvalidTransaction errors will reject the block,
        # and generic python errors will not be caught and will result in the
        # transaction processor crashing.
        except (InvalidTransaction, InternalError) as e:
            # Directly forward any sawtooth exceptions
            raise e
        except Exception as e:
            # Catch any non-sawtooth exceptions at a high level, and declare
            # the transaction invalid. Clients may retry as needed.
            LOGGER.exception(e)
            raise InvalidTransaction("An unhandled transaction processing "
                                     "exception occurred") from e


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
        _add_net(action_payload, context)
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
    data = _get_state_data(address, context)
    if data:
        raise InvalidTransaction('The user {} already exists'.format(imsi))

    user_state = {'id': imsi, 'pub_key': pub_key, 'home_net': home_network}
    _set_state_data(address, user_state, context)


def _add_net(serialized_payload, context):
    # TODO(matt9j) Do a more safe deserialization.
    # Parse the outer data layer from wire format
    data = cbor.loads(serialized_payload)
    raw_message = data['msg']
    signature = data['network_sig']

    # Parse the inner message from wire format
    message = cbor.loads(raw_message)
    key = nacl.signing.VerifyKey(message['key'], encoder=nacl.encoding.RawEncoder)
    verified = key.verify(raw_message, signature, encoder=nacl.encoding.RawEncoder)

    if not verified:
        raise InvalidTransaction('Message failed network key validation')

    # TODO(matt9j) ensure we are not blowing away existing state.
    net_state = {'verify_key': message['key']}
    _set_state_data(make_network_address(message['network_id']), net_state, context)


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
