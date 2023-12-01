from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from zipfile import ZipFile
import os
from datetime import datetime

# Opprett en Flask-applikasjon
app = Flask(__name__)

# Opplastingsmappe for filer som skal mottas
UPLOAD_FOLDER = 'received_data'
ALLOWED_EXTENSIONS = {'zip'}

# Konfigurer opplastingsmappen for appen
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Opprett opplastingsmappen hvis den ikke eksisterer
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Funksjon for å sjekke om en filtype er tillatt basert på dens filendelse
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rutehandler for å laste opp og behandle mottatte filer
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        directory_name = f"Directory_for_detection_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
        directory_path = os.path.join(app.config['UPLOAD_FOLDER'], directory_name + ".zip")

        try:
            file.save(directory_path)
            with ZipFile(directory_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(app.config['UPLOAD_FOLDER'], directory_name))
            print(f"File {filename} has been uploaded and extracted.")
            return jsonify({"status": "success"})
        except Exception as e:
            print("Exception occurred: ", e)
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "error", "message": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

