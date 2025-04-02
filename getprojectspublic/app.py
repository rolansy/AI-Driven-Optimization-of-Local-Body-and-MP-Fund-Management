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
import sqlite3
from fpdf import FPDF

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
DATABASE = 'prioritized_projects.db'

# Load NLP model (Using spaCy as an example, replace with API if needed)
nlp = spacy.load("en_core_web_sm")

# Initialize geolocator
geolocator = Nominatim(user_agent="project_portal")

# Configure Google Generative AI
genai.configure(api_key="AIzaSyBYQ5SgfI8mtSnJftWmZduop8TTuDpdzWQ")

# Load project plans CSV
df = pd.read_csv("prioritisation/project_plans.csv")

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

# Initialize the database
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prioritized_projects (
                    Project_ID TEXT PRIMARY KEY,
                    Project_Name TEXT,
                    Category TEXT,
                    Estimated_Cost INTEGER,
                    Start_Year INTEGER,
                    End_Year INTEGER,
                    Duration INTEGER,
                    Category_Weight INTEGER,
                    Duration_Score REAL,
                    Cost_Score REAL,
                    Category_Encoded INTEGER,
                    Priority_Score REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    count INTEGER,
                    latitude REAL,
                    longitude REAL,
                    area TEXT,
                    user_input TEXT
                )''')
    conn.commit()
    conn.close()

# Update the database schema to include user_input
def update_db_schema():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Add user_input column if it doesn't already exist
    c.execute("PRAGMA table_info(projects)")
    columns = [column[1] for column in c.fetchall()]
    if "user_input" not in columns:
        c.execute("ALTER TABLE projects ADD COLUMN user_input TEXT")
    conn.commit()
    conn.close()

# Load initial data into the database
def load_initial_data():
    conn = sqlite3.connect(DATABASE)
    df_prioritized = pd.read_csv("prioritisation/prioritized_project_plans.csv")
    df_prioritized.to_sql('prioritized_projects', conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()

# Calculate priority scores and update the database
def calculate_priority_scores():
    global df
    df["Category_Weight"] = df["Category"].map(category_weightage).fillna(0)
    scaler = MinMaxScaler()
    df["Duration_Score"] = 1 - scaler.fit_transform(df[["Duration"]].copy())
    df["Cost_Score"] = 1 - scaler.fit_transform(df[["Estimated_Cost (INR)"]].copy())
    label_encoder = LabelEncoder()
    df["Category_Encoded"] = label_encoder.fit_transform(df["Category"])
    df["Priority_Score"] = df["Category_Weight"] * 0.5 + df["Duration_Score"] * 0.25 + df["Cost_Score"] * 0.25
    df_prioritized = df.sort_values(by="Priority_Score", ascending=False)
    
    conn = sqlite3.connect(DATABASE)
    df_prioritized.to_sql('prioritized_projects', conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()

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
    global df  # Ensure we modify the global dataframe
    report_text = extract_text_from_pdf(pdf_path)
    if not report_text:
        print("No text extracted from PDF.")
        return None, None, None

    project_details = extract_project_details(report_text)
    print(f"Extracted Project Details: {project_details}")  # Debugging

    if not project_details or "Project_Name" not in project_details:
        print("No valid project details extracted.")
        return None, None, None

    # Validate and convert extracted details
    try:
        new_row = {
            "Project_Name": project_details.get("Project_Name", "Unknown"),
            "Category": project_details.get("Category", "Unknown"),
            "Estimated_Cost (INR)": float(
                str(project_details.get("Estimated_Cost (INR)", "0")).replace(',', '') 
                if str(project_details.get("Estimated_Cost (INR)", "0")).replace(',', '').replace('.', '').isdigit() 
                else 0
            ),
            "Start_Year": int(
                str(project_details.get("Start_Year", "0")) 
                if str(project_details.get("Start_Year", "0")).isdigit() 
                else 0
            ),
            "End_Year": int(
                str(project_details.get("End_Year", "0")) 
                if str(project_details.get("End_Year", "0")).isdigit() 
                else 0
            ),
            "Duration": int(
                str(project_details.get("Duration (Years)", "0")) 
                if str(project_details.get("Duration (Years)", "0")).isdigit() 
                else 0
            )
        }
    except ValueError as e:
        print(f"Error converting project details: {e}")
        return None, None, None

    # Add new row to project_plans.csv
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)  # Fix for Pandas 2.0+
    df.to_csv("prioritisation/project_plans.csv", index=False)  # Save updated project plans CSV

    # Recalculate priority scores and update the database
    calculate_priority_scores()

    # Get the rank and score of the new project
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT rowid, Priority_Score FROM prioritized_projects WHERE Project_Name = ?", (new_row["Project_Name"],))
    result = c.fetchone()
    conn.close()
    
    if result:
        new_project_rank = result[0]
        new_project_score = result[1]
        print(f"New project added successfully! Its score is: {new_project_score} and its rank in the priority list is: {new_project_rank}")
        return new_project_rank, new_project_score, project_details
    else:
        print("Error: The new project was not found in the database.")
        return None, None, None

# NLP-based project classification
def classify_project(user_input):
    doc = nlp(user_input.lower())
    
    # Example keyword-based mapping (extendable)
    sectors = {
        "infrastructure": ["road", "bridge", "water supply", "electricity", "sewage system", "public transport"],
        "education": ["school", "library", "college", "university", "training center"],
        "healthcare": ["hospital", "clinic", "ambulance", "health center", "medical camp"],
        "public welfare": ["park", "community hall", "waste management", "shelter", "food distribution"]
    }
    
    project_name = None
    project_sector = "others"
    
    # Create a PhraseMatcher object
    matcher = PhraseMatcher(nlp.vocab)
    
    # Add patterns to the matcher
    for sector, keywords in sectors.items():
        patterns = [nlp(keyword) for keyword in keywords]
        matcher.add(sector, patterns)
    
    # Find matches in the user input
    matches = matcher(doc)
    
    if matches:
        match_id, start, end = matches[0]
        project_sector = nlp.vocab.strings[match_id]
        project_name = doc[start:end].lemma_  # Use lemma_ to get the base form
    
    return project_name, project_sector

# Get area name based on latitude and longitude
def get_area_name(latitude, longitude):
    location = geolocator.reverse((latitude, longitude), exactly_one=True)
    return location.address if location else "Unknown"

# Add or update a project in the database
def add_or_update_project(name, sector, latitude, longitude, user_input):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Define a close radius (e.g., 10 km)
    close_radius = 10.0  # in kilometers
    
    # Check for existing projects within the close radius
    c.execute("SELECT * FROM projects WHERE name = ? AND sector = ?", (name, sector))
    projects = c.fetchall()
    
    for project in projects:
        project_lat = project[4]
        project_lon = project[5]
        distance = geodesic((latitude, longitude), (project_lat, project_lon)).km
        if distance <= close_radius:
            # Update the count and user_input for the existing project
            c.execute("UPDATE projects SET count = count + 1, user_input = ? WHERE id = ?", (user_input, project[0]))
            conn.commit()
            conn.close()
            return
    
    # If no close project is found, insert a new project
    area_name = get_area_name(latitude, longitude)
    c.execute(
        "INSERT INTO projects (name, sector, count, latitude, longitude, area, user_input) VALUES (?, ?, 1, ?, ?, ?, ?)",
        (name, sector, latitude, longitude, area_name, user_input)
    )
    conn.commit()
    conn.close()

# API Endpoint to upload PDF and process it
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            rank, score, details = add_project_from_pdf(file_path)
            print(f"Extracted Project Details: {details}")  # Debugging
            if rank is not None and score is not None and details:
                return jsonify({
                    "message": "Project added successfully",
                    "rank": rank,
                    "score": score,
                    "project_details": details
                })
            else:
                return jsonify({"error": "Failed to process PDF"}), 500
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return jsonify({"error": "Internal server error"}), 500

# API Endpoint to get prioritized projects
@app.route("/prioritized_projects", methods=["GET"])
def get_prioritized_projects():
    try:
        conn = sqlite3.connect(DATABASE)
        df_prioritized = pd.read_sql_query("SELECT * FROM prioritized_projects ORDER BY Priority_Score DESC", conn)
        conn.close()
        projects = df_prioritized.to_dict(orient="records")
        return jsonify(projects)
    except Exception as e:
        print(f"Error fetching prioritized projects: {e}")
        return jsonify({"error": "Internal server error"}), 500

# API Endpoint to clear the PDF output
@app.route("/clear_output", methods=["POST"])
def clear_output():
    try:
        global df
        df = pd.read_csv("prioritisation/project_plans.csv")
        calculate_priority_scores()
        return jsonify({"message": "Output cleared successfully"})
    except Exception as e:
        print(f"Error clearing output: {e}")
        return jsonify({"error": "Internal server error"}), 500

# API Endpoint for user input
@app.route("/submit", methods=["POST"])
def submit_request():
    data = request.get_json()
    user_input = data.get("text", "")
    latitude = data.get("latitude", None)
    longitude = data.get("longitude", None)

    if not user_input or latitude is None or longitude is None:
        return jsonify({"error": "Incomplete input provided"}), 400

    project_name, sector = classify_project(user_input)
    if project_name:
        add_or_update_project(project_name, sector, latitude, longitude, user_input)
        return jsonify({"message": "Project request recorded", "category": sector, "project": project_name})
    else:
        return jsonify({"error": "No valid project found"}), 400

# API Endpoint to get project list
@app.route("/projects", methods=["GET"])
def get_projects():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM projects ORDER BY count DESC")
    projects = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": row[0],
            "name": row[1],
            "sector": row[2],
            "count": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "area": row[6],
            "user_input": row[7]
        }
        for row in projects
    ])

# API Endpoint to clear the database
@app.route("/clear", methods=["POST"])
def clear_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM projects")
    conn.commit()
    conn.close()
    return jsonify({"message": "Database cleared"})

# API Endpoint to generate PDF for a project
@app.route('/generate_pdf/<int:project_id>', methods=['GET'])
def generate_pdf(project_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = c.fetchone()
        conn.close()

        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Extract project details
        project_name = project[1]
        sector = project[2]
        user_input = project[7]
        latitude = project[4]
        longitude = project[5]

        # Define market rates (ensure this is available in the function)
        market_rates = {
            "Road Construction": 1000000,
            "School Building": 2000000,
            "Hospital Equipment": 1500000,
            "Water Supply": 800000,
            "Park Development": 500000,
            "Tourism": 1000000  # Added entry for Tourism
        }

        # Fetch market rate
        estimated_cost = market_rates.get(sector, "Unknown")

        # Generate start year, end year, and duration
        from datetime import datetime
        start_year = datetime.now().year
        duration_years = 2  # Example duration
        end_year = start_year + duration_years

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Project Report", ln=True, align='C')
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Project Name: {project_name}", ln=True)
        pdf.cell(200, 10, txt=f"Sector: {sector}", ln=True)
        pdf.cell(200, 10, txt=f"User Input: {user_input}", ln=True)
        pdf.cell(200, 10, txt=f"Latitude: {latitude}", ln=True)
        pdf.cell(200, 10, txt=f"Longitude: {longitude}", ln=True)
        pdf.cell(200, 10, txt=f"Estimated Cost (INR): {estimated_cost}", ln=True)
        pdf.cell(200, 10, txt=f"Start Year: {start_year}", ln=True)
        pdf.cell(200, 10, txt=f"End Year: {end_year}", ln=True)
        pdf.cell(200, 10, txt=f"Duration (Years): {duration_years}", ln=True)

        # Save PDF to a temporary file
        pdf_output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{project_name}_report.pdf")
        pdf.output(pdf_output_path)

        # Serve the PDF file
        return send_from_directory(app.config['UPLOAD_FOLDER'], f"{project_name}_report.pdf", as_attachment=False)

    except Exception as e:
        print(f"Error generating PDF: {e}")
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
    init_db()
    update_db_schema()  # Update the schema
    load_initial_data()
    app.run(debug=True)