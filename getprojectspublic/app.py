from flask import Flask, request, jsonify, render_template, send_from_directory
import pandas as pd
import numpy as np
import spacy
from spacy.matcher import PhraseMatcher
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor
import fitz  # PyMuPDF
import os
import re
import json
import google.generativeai as genai

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Load NLP model (Using spaCy as an example, replace with API if needed)
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="project_portal")

# Configure Google Generative AI
genai.configure(api_key="AIzaSyBYQ5SgfI8mtSnJftWmZduop8TTuDpdzWQ")

# Load project plans CSV
df = pd.read_csv("prioritisation/project_plans.csv")
df_prioritized = df.copy()

# Define category weightage
category_weightage = {
    "Healthcare": 10,
    "Infrastructure": 9,
    "Education": 8,
    "Water & Sanitation": 8,
    "Energy": 7,
    "Transport": 6,
    "Environment": 5,
    "Social Welfare": 4,
    "Tourism": 3,
    "IT & Digital Services": 3
}

# Calculate priority scores
def calculate_priority_scores():
    global df_prioritized
    df_prioritized["Category_Weight"] = df_prioritized["Category"].map(category_weightage).fillna(0)
    scaler = MinMaxScaler()
    df_prioritized["Duration_Score"] = 1 - scaler.fit_transform(df_prioritized[["Duration"]].copy())
    df_prioritized["Cost_Score"] = 1 - scaler.fit_transform(df_prioritized[["Estimated_Cost (INR)"]].copy())
    label_encoder = LabelEncoder()
    df_prioritized["Category_Encoded"] = label_encoder.fit_transform(df_prioritized["Category"])
    df_prioritized["Priority_Score"] = df_prioritized["Category_Weight"] * 0.5 + df_prioritized["Duration_Score"] * 0.25 + df_prioritized["Cost_Score"] * 0.25
    df_prioritized = df_prioritized.sort_values(by="Priority_Score", ascending=False)
    df_prioritized.to_csv("prioritisation/prioritized_project_plans.csv", index=False)

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)  # Using fitz instead of pymupdf
        text = "\n".join([page.get_text("text") for page in doc])
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

# Extract project details from text using Google API
def extract_project_details(report_text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Extract the following details from the given project report:
    - Project_Name
    - Category
    - Estimated_Cost (INR)
    - Start_Year
    - End_Year
    - Duration (Years)
    
    Report: {report_text}
    
    Provide the response in **valid** JSON format, with no extra explanations."""
    
    response = model.generate_content(prompt)
    print("Raw Gemini API response:", response.text)  # Debugging

    try:
        # Extract JSON from response using regex
        json_text = re.search(r"\{.*\}", response.text, re.DOTALL)
        if json_text:
            return json.loads(json_text.group())  # Parse valid JSON
        else:
            print("No JSON detected in response.")
            return {}
    except json.JSONDecodeError:
        print("Error parsing response from Gemini API.")
        return {}

# Add project from PDF
def add_project_from_pdf(pdf_path):
    global df, df_prioritized  # Ensure we modify the global dataframes
    report_text = extract_text_from_pdf(pdf_path)
    if not report_text:
        print("No text extracted from PDF.")
        return None, None, None

    project_details = extract_project_details(report_text)
    
    if not project_details:
        print("No valid project details extracted.")
        return None, None, None

    new_row = {
        "Project_Name": project_details.get("Project_Name", "Unknown"),
        "Category": project_details.get("Category", "Unknown"),
        "Estimated_Cost (INR)": project_details.get("Estimated_Cost (INR)", 0),
        "Start_Year": project_details.get("Start_Year", 0),
        "End_Year": project_details.get("End_Year", 0),
        "Duration": project_details.get("Duration (Years)", 0)
    }

    # Add new row to project_plans.csv
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)  # Fix for Pandas 2.0+
    df.to_csv("prioritisation/project_plans.csv", index=False)  # Save updated project plans CSV

    # Recalculate priority scores and reorder projects
    calculate_priority_scores()

    # Print the score and rank of the new project
    new_project_rank = df_prioritized.reset_index().index[df_prioritized["Project_Name"] == new_row["Project_Name"]][0] + 1
    new_project_score = df_prioritized[df_prioritized["Project_Name"] == new_row["Project_Name"]]["Priority_Score"].values[0]
    print(f"New project added successfully! Its score is: {new_project_score} and its rank in the priority list is: {new_project_rank}")
    return new_project_rank, new_project_score, project_details

# API Endpoint to upload PDF and process it
@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            rank, score, project_details = add_project_from_pdf(file_path)
            if rank is None or score is None or project_details is None:
                return jsonify({"error": "Failed to process PDF"}), 500
            return jsonify({"rank": int(rank), "score": float(score), "project_details": project_details})
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return jsonify({"error": "Internal server error"}), 500

# API Endpoint to get prioritized projects
@app.route("/prioritized_projects", methods=["GET"])
def get_prioritized_projects():
    try:
        df_prioritized = pd.read_csv("prioritisation/prioritized_project_plans.csv")
        df_prioritized = df_prioritized.replace({np.nan: None})  # Replace NaN with None for JSON serialization
        projects = df_prioritized.to_dict(orient="records")
        return jsonify(projects)
    except Exception as e:
        print(f"Error fetching prioritized projects: {e}")
        return jsonify({"error": "Internal server error"}), 500

# API Endpoint to clear the PDF output
@app.route("/clear_output", methods=["POST"])
def clear_output():
    try:
        global df, df_prioritized
        df = pd.read_csv("prioritisation/project_plans.csv")
        df_prioritized = df.copy()
        calculate_priority_scores()
        return jsonify({"message": "Output cleared successfully"})
    except Exception as e:
        print(f"Error clearing output: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Serve the HTML template
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/map")
def map_view():
    return render_template("map.html")

@app.route("/priority")
def priority_view():
    return render_template("priority.html")

@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)