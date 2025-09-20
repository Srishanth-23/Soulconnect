import os, tempfile, base64
from flask import Flask, request, send_file, jsonify
from google.cloud import aiplatform, storage
import functions_framework

app = Flask(__name__)

# Initialize AI Platform and Storage
aiplatform.init(
    project=os.environ['GOOGLE_CLOUD_PROJECT'],
    location=os.environ.get('REGION', 'us-central1')
)
MODEL_ENDPOINT = os.environ['AUDIO_MODEL_ENDPOINT']

@app.route('/generate-soundscape', methods=['GET'])
def generate_soundscape():
    mood = request.args.get('mood', 'calm')
    length = int(request.args.get('len', 120))

    client = aiplatform.gapic.PredictionServiceClient()
    endpoint = MODEL_ENDPOINT
    response = client.predict(
        endpoint=endpoint,
        instances=[{'mood': mood, 'length': length}],
        parameters={}
    )

    audio_b64 = response.predictions[0].get('audio', '')
    if not audio_b64:
        return jsonify({'error': 'No audio returned'}), 500

    audio_bytes = base64.b64decode(audio_b64)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
    tmp.write(audio_bytes)
    tmp.flush()
    return send_file(tmp.name, mimetype='audio/ogg')

# Entry point for Cloud Run
@functions_framework.http
def app_entry(request):
    return app(request.environ, lambda status, headers: None)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
