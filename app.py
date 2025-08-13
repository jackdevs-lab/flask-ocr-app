import os
import io
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_image(image):
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes)
    text = ""
    for image in images:
        text += extract_text_from_image(image) + "\n"
    return text

def create_docx(text):
    doc = Document()
    doc.add_paragraph(text)
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def create_pdf(text):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    text_obj = c.beginText(40, 750)
    
    # Split text into lines that fit the page
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if c.stringWidth(test_line) < 500:  # Rough page width check
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
    
    # Add lines to the PDF
    for line in lines:
        text_obj.textLine(line)
    
    c.drawText(text_obj)
    c.save()
    output.seek(0)
    return output

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        output_format = request.form.get('format', 'txt')
        
        try:
            # Process the file based on its type
            if file.filename.lower().endswith('.pdf'):
                pdf_bytes = file.read()
                extracted_text = extract_text_from_pdf(pdf_bytes)
            else:
                image = Image.open(file.stream)
                extracted_text = extract_text_from_image(image)
            
            # Generate output in requested format
            if output_format == 'docx':
                output = create_docx(extracted_text)
                mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                extension = 'docx'
            elif output_format == 'pdf':
                output = create_pdf(extracted_text)
                mimetype = 'application/pdf'
                extension = 'pdf'
            else:  # txt
                output = io.BytesIO(extracted_text.encode('utf-8'))
                mimetype = 'text/plain'
                extension = 'txt'
            
            # Return the file data and metadata
            return jsonify({
                'filename': f'extracted_text.{extension}',
                'mimetype': mimetype,
                'file_data': output.getvalue().hex()
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/download', methods=['POST'])
def download_file():
    data = request.json
    file_data = bytes.fromhex(data['file_data'])
    filename = data['filename']
    mimetype = data['mimetype']
    
    return send_file(
        io.BytesIO(file_data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
