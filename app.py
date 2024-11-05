import os
from flask import Flask, render_template, request, send_file, after_this_request, flash, redirect, url_for
import subprocess

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required to use flash messages

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/encrypt', methods=['POST'])
def encrypt():
    cover_file = request.files['cover_file']
    text_to_hide = request.form['text_to_hide']
    password = request.form.get('password')

    # Ensure password is provided, default to 123 if none is provided
    if not password:
        flash("Empty password not allowed. Please enter the default password '123'.")
        return redirect(url_for('index'))

    cover_path = os.path.join(UPLOAD_FOLDER, 'cover_file.jpg')
    hidden_file_path = os.path.join(UPLOAD_FOLDER, 'hidden_file.txt')
    output_path = os.path.join(UPLOAD_FOLDER, 'output.jpg')

    # Save the cover file
    cover_file.save(cover_path)

    # Write the text to hide to a temporary file
    with open(hidden_file_path, 'w') as hidden_file:
        hidden_file.write(text_to_hide)

    # Build the steghide command for embedding
    cmd = ["steghide", "embed", "-cf", cover_path, "-ef", hidden_file_path, "-sf", output_path, "-p", password]

    # Run the steghide command
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        flash(f"Encryption failed: {result.stderr}")
        return redirect(url_for('index'))

    @after_this_request
    def cleanup(response):
        # Remove temporary files
        os.remove(cover_path)
        os.remove(hidden_file_path)
        os.remove(output_path)
        return response

    return send_file(output_path, as_attachment=True)

@app.route('/decrypt', methods=['POST'])
def decrypt():
    encrypted_file = request.files['encrypted_file']
    password = request.form.get('password', '')

    encrypted_path = os.path.join(UPLOAD_FOLDER, 'encrypted_file.jpg')
    output_text_path = os.path.join(UPLOAD_FOLDER, 'extracted_text.txt')

    # Save the encrypted file
    encrypted_file.save(encrypted_path)

    # Attempt decryption with user-provided password
    success = False
    cmd = ["steghide", "extract", "-sf", encrypted_path, "-xf", output_text_path, "-p", password]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # If first attempt fails, try the universal password "sam"
    if result.returncode != 0:
        cmd = ["steghide", "extract", "-sf", encrypted_path, "-xf", output_text_path, "-p", "sam"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            success = True
    else:
        success = True

    @after_this_request
    def cleanup(response):
        # Remove temporary files
        os.remove(encrypted_path)
        if os.path.exists(output_text_path):
            os.remove(output_text_path)
        return response

    if success:
        # Read and return the extracted hidden text
        with open(output_text_path, 'r') as extracted_file:
            hidden_text = extracted_file.read()
        return f"Hidden Text: {hidden_text}"
    else:
        flash("Wrong password.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)