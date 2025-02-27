from flask import Flask, request, jsonify, render_template
import sqlite3
import spacy

app = Flask(__name__)

# Load NLP model (Using spaCy as an example, replace with API if needed)
nlp = spacy.load("en_core_web_sm")

# Database setup
def init_db():
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id INTEGER PRIMARY KEY, name TEXT, sector TEXT, count INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# NLP-based project classification
def classify_project(user_input):
    doc = nlp(user_input.lower())
    
    # Example keyword-based mapping (extendable)
    sectors = {
        "infrastructure": ["road", "bridge", "water supply", "electricity"],
        "education": ["school", "library", "college", "university"],
        "healthcare": ["hospital", "clinic", "ambulance", "health center"],
        "public welfare": ["park", "community hall", "waste management"]
    }
    
    project_name = None
    project_sector = "others"
    
    for sector, keywords in sectors.items():
        for word in doc:
            if word.text in keywords:
                project_name = word.text
                project_sector = sector
                break
        if project_name:
            break
    
    return project_name, project_sector

# Add or update a project in the database
def add_or_update_project(name, sector):
    conn = sqlite3.connect("projects.db")
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE name = ? AND sector = ?", (name, sector))
    project = c.fetchone()
    
    if project:
        c.execute("UPDATE projects SET count = count + 1 WHERE name = ? AND sector = ?", (name, sector))
    else:
        c.execute("INSERT INTO projects (name, sector, count) VALUES (?, ?, 1)", (name, sector))
    
    conn.commit()
    conn.close()

# API Endpoint for user input
@app.route("/submit", methods=["POST"])
def submit_request():
    data = request.get_json()
    user_input = data.get("text", "")
    
    if not user_input:
        return jsonify({"error": "No input provided"}), 400
    
    project_name, sector = classify_project(user_input)
    if project_name:
        add_or_update_project(project_name, sector)
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
    
    return jsonify([{"name": row[1], "sector": row[2], "count": row[3]} for row in projects])

# Serve the HTML template
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    app.run(debug=True)