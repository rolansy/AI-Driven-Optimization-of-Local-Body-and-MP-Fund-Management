from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import spacy
from spacy.matcher import PhraseMatcher

app = Flask(__name__)

# Load NLP model (Using spaCy as an example, replace with API if needed)
nlp = spacy.load("en_core_web_sm")

# Database setup
def init_db():
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id INTEGER PRIMARY KEY, name TEXT, sector TEXT, count INTEGER, latitude REAL, longitude REAL)''')
    conn.commit()
    conn.close()

init_db()

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

# Add or update a project in the database
def add_or_update_project(name, sector, latitude, longitude):
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE name = ? AND sector = ? AND latitude = ? AND longitude = ?", (name, sector, latitude, longitude))
    project = c.fetchone()
    
    if project:
        c.execute("UPDATE projects SET count = count + 1 WHERE name = ? AND sector = ? AND latitude = ? AND longitude = ?", (name, sector, latitude, longitude))
    else:
        c.execute("INSERT INTO projects (name, sector, count, latitude, longitude) VALUES (?, ?, 1, ?, ?)", (name, sector, latitude, longitude))
    
    conn.commit()
    conn.close()

# API Endpoint for user input
@app.route("/submit", methods=["POST"])
def submit_request():
    data = request.get_json()
    user_input = data.get("text", "")
    latitude = data.get("latitude", None)
    longitude = data.get("longitude", None)
    
    print(f"Received data: {data}")  # Debugging statement
    
    if not user_input or latitude is None or longitude is None:
        return jsonify({"error": "Incomplete input provided"}), 400
    
    project_name, sector = classify_project(user_input)
    if project_name:
        add_or_update_project(project_name, sector, latitude, longitude)
        return jsonify({"message": "Project request recorded", "category": sector, "project": project_name})
    else:
        return jsonify({"error": "No valid project found"}), 400

# API Endpoint to get project list
@app.route("/projects", methods=["GET"])
def get_projects():
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute("SELECT * FROM projects ORDER BY count DESC")
    projects = c.fetchall()
    conn.close()
    
    return jsonify([{"name": row[1], "sector": row[2], "count": row[3], "latitude": row[4], "longitude": row[5]} for row in projects])

# API Endpoint to clear the database
@app.route("/clear", methods=["POST"])
def clear_database():
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute("DELETE FROM projects")
    conn.commit()
    conn.close()
    return jsonify({"message": "Database cleared"})

# Serve the HTML template
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/map")
def map_view():
    return render_template("map.html")

@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    app.run(debug=True)