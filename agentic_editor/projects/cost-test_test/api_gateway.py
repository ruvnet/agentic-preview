from flask import Flask, request, jsonify
import jwt
import requests
import logging
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure secret key
logging.basicConfig(level=logging.INFO)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            logging.warning("Request received without token")
            return jsonify({"message": "Token is missing"}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            logging.info(f"Token decoded successfully for user: {data.get('user_id')}")
        except jwt.ExpiredSignatureError:
            logging.warning("Expired token received")
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            logging.warning("Invalid token received")
            return jsonify({"message": "Token is invalid"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@token_required
def api_gateway(path):
    try:
        logging.info(f"Routing request to: {path}")
        response = requests.request(
            method=request.method,
            url=f"http://localhost:5001/{path}",
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)
        
        logging.info(f"Response received with status code: {response.status_code}")
        return (response.content, response.status_code, response.headers.items())
    except requests.RequestException as e:
        logging.error(f"Error routing request: {str(e)}")
        return jsonify({"message": "Error routing request"}), 500

if __name__ == '__main__':
    app.run(port=5002)
