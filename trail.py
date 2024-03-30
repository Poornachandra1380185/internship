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
import re

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

            # Define regular expressions for extraction
            name_pattern = r"Name:\s*(.*)"
            gender_pattern = r"Gender:\s*(.*)"
            dob_pattern = r"DOB:\s*(.*)"
            aadhar_pattern = r"Aadhar:\s*(.*)"

            # Extract information using regular expressions
            name_match = re.search(name_pattern, extracted_text)
            gender_match = re.search(gender_pattern, extracted_text)
            dob_match = re.search(dob_pattern, extracted_text)
            aadhar_match = re.search(aadhar_pattern, extracted_text)

            # Extracted values
            name = name_match.group(1) if name_match else None
            gender = gender_match.group(1) if gender_match else None
            dob = dob_match.group(1) if dob_match else None
            aadhar = aadhar_match.group(1) if aadhar_match else None

            # Insert extracted data into MongoDB
            upload_data = {
                'filename': filename,
                'path': file_path,
                'name': name,
                'gender': gender,
                'dob': dob,
                'aadhar': aadhar,
                'extracted_text': extracted_text
            }
            uploads_collection.insert_one(upload_data)

            extracted_data = list(uploads_collection.find())

        except Exception as e:
            return f"An error occurred: {str(e)}"

    return render_template('index.html', form=form, extracted_data=extracted_data)



if __name__ == '__main__':
    app.run(debug=True)
