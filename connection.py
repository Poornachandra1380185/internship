from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
import ssl
import textract
import fitz
import pytesseract
import cv2
import numpy as np
from pymongo import MongoClient

pytesseract.pytesseract.tesseract_cmd = r'path_to_tesseract'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/files'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
context = ssl._create_unverified_context()

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['file_upload_db']
uploads_collection = db['uploads']
extracted_text_collection = db['extracted_text']

# Load the template images for name, gender, and date of birth
name_template = cv2.imread('name_template.jpg', cv2.IMREAD_GRAYSCALE)
gender_template = cv2.imread('gender_template.jpg', cv2.IMREAD_GRAYSCALE)
dob_template = cv2.imread('dob_template.jpg', cv2.IMREAD_GRAYSCALE)

class UploadFileForm(FlaskForm):
    file = FileField("File")
    submit = SubmitField("Upload File")

@app.route('/upload_and_extract', methods=['GET', 'POST'])
def upload_and_extract():
    form = UploadFileForm()
    extracted_data = []

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            extracted_text = ""

            if file.filename.lower().endswith(('.pdf')):
                # Extract text from PDF using PyMuPDF
                pdf_document = fitz.open(file_path)
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    extracted_text += page.get_text()
            else:
                # Extract text from image using pytesseract
                extracted_text = pytesseract.image_to_string(file_path)

                # Load the uploaded image for template matching
                extracted_image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

                # Perform template matching for name, gender, and date of birth
                name_match = cv2.matchTemplate(extracted_image, name_template, cv2.TM_CCOEFF_NORMED)
                gender_match = cv2.matchTemplate(extracted_image, gender_template, cv2.TM_CCOEFF_NORMED)
                dob_match = cv2.matchTemplate(extracted_image, dob_template, cv2.TM_CCOEFF_NORMED)

                # Identify the regions with highest similarity scores
                name_location = np.unravel_index(np.argmax(name_match), name_match.shape)
                gender_location = np.unravel_index(np.argmax(gender_match), gender_match.shape)
                dob_location = np.unravel_index(np.argmax(dob_match), dob_match.shape)

                # Extract text from the identified regions using OCR
                name_text = pytesseract.image_to_string(extracted_image[name_location[0]:name_location[0]+name_template.shape[0], name_location[1]:name_location[1]+name_template.shape[1]])
                gender_text = pytesseract.image_to_string(extracted_image[gender_location[0]:gender_location[0]+gender_template.shape[0], gender_location[1]:gender_location[1]+gender_template.shape[1]])
                dob_text = pytesseract.image_to_string(extracted_image[dob_location[0]:dob_location[0]+dob_template.shape[0], dob_location[1]:dob_location[1]+dob_template.shape[1]])

            upload_data = {
                'filename': filename,
                'path': file_path,
                'extracted_text': extracted_text,
                'name': name_text,
                'gender': gender_text,
                'dob': dob_text
            }
            uploads_collection.insert_one(upload_data)

            extracted_data = list(uploads_collection.find())

        except Exception as e:
            return f"An error occurred: {str(e)}"

    return render_template('index.html', form=form, extracted_data=extracted_data)

if __name__ == '__main__':
    app.run(debug=True)
