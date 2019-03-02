import io

from flask import Flask
from flask import request
from flask import send_file

import test_pb2 as test_proto

app = Flask(__name__)


@app.route('/test-http')
def test_http():
    print("Returning a simple string via http")
    return "This is a test http message, hello world!"


@app.route('/')
def help():
    print("Printing the help message")
    return ("Try querying \'localhost:5000/test-http\'"
            " or \'localhost:5000/test-proto\'")


@app.route('/test-proto')
def do_test_proto():
    print("Generating a proto message in python")
    proto_object = test_proto.SimpleProto()
    proto_object.message = "Hello proto world!"
    proto_object.year = 2019
    proto_object.timestamp = -123456
    proto_object.submessage.year = 554433
    proto_object.submessage.inner = "Genie in the bottle, in a bottle"
    print("The message is \'", proto_object.message, "\'")
    print("The year is \'", proto_object.year, "\'")
    print("The timestamp is \'", proto_object.timestamp, "\'")
    print("The submessage year is \'", proto_object.submessage.year, "\'")
    print("The submessage inner is \'", proto_object.submessage.inner, "\'")
    serialized_proto = proto_object.SerializeToString()
    print("When serialized that looks like:")
    print(serialized_proto)

    return send_file(io.BytesIO(serialized_proto),
                     mimetype='application/octet-stream')


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
