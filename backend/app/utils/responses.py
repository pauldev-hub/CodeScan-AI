from flask import jsonify


def success_response(payload, status_code=200):
    return jsonify(payload), status_code


def error_response(message, status, status_code):
    return jsonify({"error": message, "status": status}), status_code
