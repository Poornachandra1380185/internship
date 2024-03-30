from flask import Flask, render_template,request,redirect, url_for, flash,jsonify,session
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
from bson import ObjectId
import json
import sys
import requests
import os
from os import walk
import pytesseract
from pytesseract import image_to_string
from PIL import Image
import nltk 
from nltk import word_tokenize,sent_tokenize,ngrams
from nltk.tokenize import regexp_tokenize 
import cv2
import re
import string
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics
import pandas as pd
import numpy as np
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import io
import docx
import urllib.request
import ssl
from urllib.request import urlopen
from pdf2image import convert_from_path 
import textract
from wtforms.validators import InputRequired
from pymongo import MongoClient
import fitz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/files'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
context = ssl._create_unverified_context()

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['file_upload_db']
uploads_collection = db['uploads']


class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    submit = SubmitField("Upload File")

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    form = UploadFileForm()
    uploaded_path = None

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Store file information in MongoDB
        upload_data = {
            'filename': filename,
            'path': file_path
        }
        uploads_collection.insert_one(upload_data)

        uploaded_path = file_path  # Pass the uploaded path to the template

        # Store file path and filename in "car" collection
        uploads_data = {
            'filename': filename,
            'path': file_path
        }
        uploads_collection.insert_one(uploads_data)

    return render_template('index.html', form=form, uploaded_path=uploaded_path)


@app.route('/extract_text_from_uploads', methods=['GET'])
def extract_text_from_uploads():
    try:
        extracted_text = ""

        # Loop through the records in the "uploads" collection
        for record in uploads_collection.find():
            file_path = record['path']
            text = ""

            # Use PyMuPDF to extract text from the PDF
            pdf_document = fitz.open(file_path)
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text += page.get_text()
            extracted_text += text

        return extracted_text

    except Exception as e:
        return str(e), 500



if __name__ == '__main__':
    app.run(debug=True)
   

