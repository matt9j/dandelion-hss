Test Server Setup
-----------------

The test server requires the python server framework "flask" and
python3 to run. Install flask into your python environment with your
setup of choice (pip, conda, pipenv, etc...)! Once flask is setup you
should be able to run the server with `python3 fake_server.py.` Once
the server is running, you can access it in a web browser at
`http://localhost:5000/` It provides two resources, the first is a
simple text hello world at /test-http, and the other is a protobuf at
/test-proto
