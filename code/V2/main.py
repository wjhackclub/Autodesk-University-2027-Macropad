from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "codellama"  # Change to your installed model if needed (e.g., deepseek-coder)

@app.route('/process', methods=['POST'])
def process_ai():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON payload provided'}), 400

    text = data.get('text', '')
    mode = data.get('mode', 'complete')

    if mode == 'complete':
        prompt = f"Complete the following line of code naturally. Return ONLY the completion snippet, no markdown blocks, no explanation:\n{text}"
    elif mode == 'fix':
        prompt = f"Identify and fix any bugs in this line of code. Return ONLY the corrected line, no markdown blocks, no explanation:\n{text}"
    elif mode == 'block':
        prompt = f"Write a functional code block or program based on this instruction. Return clean code:\n{text}"
    else:
        prompt = text

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            completion = result.get('response', '').strip()
            return jsonify({'completion': completion}), 200
        else:
            return jsonify({'error': f'Ollama error status {response.status_code}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
