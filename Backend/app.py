from flask import Flask, jsonify, request
from models import db, User, Task, Category

ALLOWED_STATUSES = ["To Do", "In Progress", "Done"]

app = Flask(__name__)

# Datenbank Konfiguration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

ALLOWED_STATUSES = ["To Do", "In Progress", "Done"]


@app.route("/")
def home():
    return "Backend läuft mit User, Task & Category Modellen 🎉"


# =======================
# USER ROUTEN
# =======================

@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    user = User(username=data["username"], email=data["email"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@app.route("/users/<int:user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id):
    tasks = Task.query.filter_by(user_id=user_id).all()
    return jsonify([t.to_dict() for t in tasks])


# =======================
# TASK ROUTEN
# =======================

# ✔ Alle Tasks abrufen
@app.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([t.to_dict() for t in tasks])


# ✔ Neuen Task erstellen
@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    status = data.get("status", "To Do")
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    task = Task(
        title=data["title"],
        description=data.get("description", ""),
        status=status,
        user_id=data["user_id"],
        category_id=data.get("category_id")  # optional
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


# ✔ Task bearbeiten (Titel, Beschreibung, Status, Kategorie)
@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    task.title = data.get("title", task.title)
    task.description = data.get("description", task.description)

    # → Status ändern nur wenn vorhanden
    if "status" in data:
        new_status = data["status"]
        if new_status not in ALLOWED_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        task.status = new_status

    # → Kategorie optional ändern
    if "category_id" in data:
        task.category_id = data["category_id"]

    db.session.commit()
    return jsonify(task.to_dict())


# ⭐ NEU: Task verschieben (für Kanban: To Do → In Progress → Done)
@app.route("/tasks/<int:task_id>/move", methods=["PUT"])
def move_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}

    new_status = data.get("status")
    if new_status not in ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    task.status = new_status
    db.session.commit()
    return jsonify(task.to_dict()), 200


# ✔ Task löschen
@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task gelöscht"})


# ======================
# KATEGORIEN
# ======================

# Alle Kategorien holen
@app.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories]), 200


# Neue Kategorie anlegen
@app.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"error": "Category name is required"}), 400

    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


# Einzelne Kategorie anzeigen
@app.route("/categories/<int:category_id>", methods=["GET"])
def get_category(category_id):
    category = Category.query.get_or_404(category_id)
    return jsonify(category.to_dict()), 200


# Kategorie-Namen ändern
@app.route("/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    category = Category.query.get_or_404(category_id)
    data = request.get_json()

    new_name = data.get("name")
    if not new_name:
        return jsonify({"error": "New name is required"}), 400

    category.name = new_name
    db.session.commit()
    return jsonify(category.to_dict()), 200


# Kategorie löschen
@app.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    # Alle Tasks dieser Kategorie entkoppeln
    tasks = Task.query.filter_by(category_id=category_id).all()
    for t in tasks:
        t.category_id = None

    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category gelöscht und Tasks entkoppelt"}), 200


# Alle Tasks einer Kategorie
@app.route("/categories/<int:category_id>/tasks", methods=["GET"])
def get_tasks_by_category(category_id):
    tasks = Task.query.filter_by(category_id=category_id).all()
    return jsonify([t.to_dict() for t in tasks]), 200

# =======================
# Board
# =======================
@app.route("/board", methods=["GET"])
def get_board():
    tasks = Task.query.all()

    # Nach Status sortieren
    columns = {
        "To Do": [],
        "In Progress": [],
        "Done": []
    }

    for t in tasks:
        status = t.status if t.status in columns else "To Do"
        columns[status].append(t.to_dict())

    # Frontend-freundliche Keys
    return jsonify({
        "todo": columns["To Do"],
        "in_progress": columns["In Progress"],
        "done": columns["Done"]
    }), 200

# =======================
# Datenbank erstellen und App starten
# =======================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)