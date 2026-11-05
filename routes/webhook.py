from flask import Blueprint, request, jsonify
import subprocess
import os

webhook_bp = Blueprint('webhook', __name__)

WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'fa048893c7bf0d4dd138c0fb0452dd11c589d659')

@webhook_bp.route('/webhook', methods=['POST'])
def github_webhook():
    # Security: Require secret token in header
    token = request.headers.get('X-Webhook-Token')
    if token != WEBHOOK_SECRET:
        return jsonify(success=False, error='Unauthorized'), 403
    try:
        repo_path = os.path.dirname(os.path.dirname(__file__))  # Root of your project
        result = subprocess.run(
            ['git', 'pull'],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return jsonify(success=True, output=result.stdout)
        else:
            return jsonify(success=False, error=result.stderr), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
