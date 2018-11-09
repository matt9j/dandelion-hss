# dandelion-hss
A distributed HSS based on sharing of single use auth tokens

# Building

dandelion uses containerized build and run environments. To run with a default test
network and a locally built CRDT processor, simply run `docker-compose build` and
`docker-compose up` from the root directory.

# Things to do:
Track tower identities as entities allowed to submit transactions "on the chain"
Track tower identities as signers for crdt updates
tracker user identities as signers for crdt updates

Track the user's home network
Track the user's 2 months of CRDTs (just need the amt. and UUID, can drop the sigs once validated)
Track the user's finalized balance
Potentially track the user's current balance.

Track the towers' current balances

*** Do I need to keep track of the n^2 who owes who graph with users in the middle? ***
- Can it just be debts between towers?


Figure out exactly what gets sent between two validators when a transaction is communicated
