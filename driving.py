from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
import ssl
import fitz
import pytesseract
import cv2
import numpy as np
from pymongo import MongoClient

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

# Load the template images for dl_no, name, and date of birth
dl_no_template = cv2.imread('dl_no_template.jpg', cv2.IMREAD_GRAYSCALE)
name_template = cv2.imread('name_template.jpg', cv2.IMREAD_GRAYSCALE)
dob_template = cv2.imread('dob_template.jpg', cv2.IMREAD_GRAYSCALE)

desired_name_length = 12  # Change this to the desired length

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
            # Extract text from image using pytesseract
            extracted_text = pytesseract.image_to_string(file_path)

            # Load the uploaded image for template matching
            extracted_image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

            # Perform template matching for dl_no, name, and date of birth
            dl_no_match = cv2.matchTemplate(extracted_image, dl_no_template, cv2.TM_CCOEFF_NORMED)
            name_match = cv2.matchTemplate(extracted_image, name_template, cv2.TM_CCOEFF_NORMED)
            dob_match = cv2.matchTemplate(extracted_image, dob_template, cv2.TM_CCOEFF_NORMED)

            # Identify the regions with highest similarity scores
            dl_no_location = np.unravel_index(np.argmax(dl_no_match), dl_no_match.shape)
            name_location = np.unravel_index(np.argmax(name_match), name_match.shape)
            dob_location = np.unravel_index(np.argmax(dob_match), dob_match.shape)

            # Extract text from the identified regions using OCR
            dl_no_text = pytesseract.image_to_string(extracted_image[dl_no_location[0]:dl_no_location[0]+dl_no_template.shape[0], dl_no_location[1]:dl_no_location[1]+dl_no_template.shape[1]])
            name_start_x = name_location[1]
            name_end_x = name_location[1] + desired_name_length
            name_text = pytesseract.image_to_string(extracted_image[name_location[0]:name_location[0]+name_template.shape[0], name_start_x:name_end_x])
            dob_text = pytesseract.image_to_string(extracted_image[dob_location[0]:dob_location[0]+dob_template.shape[0], dob_location[1]:dob_location[1]+dob_template.shape[1]])

            upload_data = {
                'filename': filename,
                'path': file_path,
                'extracted_text': extracted_text,
                'dl_no': dl_no_text,
                'name': name_text,
                'dob': dob_text
            }
            uploads_collection.insert_one(upload_data)

            extracted_data = list(uploads_collection.find())

        except Exception as e:
            return f"An error occurred: {str(e)}"

    return render_template('index.html', form=form, extracted_data=extracted_data)

if __name__ == '__main__':
    app.run(debug=True)
