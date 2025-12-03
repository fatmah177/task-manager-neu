from flask import Flask, jsonify, request
from models import db, User, Task, Category
from sqlalchemy import case
from datetime import datetime,timedelta
from flask_cors import CORS
#F#sdjf

ALLOWED_STATUSES = ["To Do", "In Progress", "Done"]
ALLOWED_PRIORITIES = ["low", "medium", "high"]

app = Flask(__name__)

CORS(app)


# Datenbank Konfiguration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)



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
    priority_order = case(
        (Task.priority == "high", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "low", 3),
        else_=4,
    )

    tasks = (
        Task.query
        .filter_by(user_id=user_id)
        .order_by(priority_order, Task.id.asc())
        .all()
    )

    return jsonify([t.to_dict() for t in tasks])


# =======================
# TASK ROUTEN
# =======================

# ✔ Alle Tasks abrufen
@app.route("/tasks", methods=["GET"])
def get_tasks():
    # Sortierreihenfolge definieren
    priority_order = case(
        (Task.priority == "high", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "low", 3),
        else_=4,
    )

    # Basis-Query
    query = Task.query

    # 🔹 Optionaler Filter: ?priority=high / medium / low
    priority_filter = request.args.get("priority")
    if priority_filter:
        priority_filter = priority_filter.lower()
        if priority_filter not in ALLOWED_PRIORITIES:
            return jsonify(
                {"error": "Invalid priority filter, allowed: low, medium, high"}
            ), 400
        query = query.filter_by(priority=priority_filter)

    # Immer sortiert zurückgeben
    tasks = query.order_by(priority_order, Task.id.asc()).all()

    return jsonify([t.to_dict() for t in tasks])

# ✔ Neuen Task erstellen
@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()

    status = data.get("status", "To Do")
    if status not in ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    priority = data.get("priority", "medium").lower()
    if priority not in ALLOWED_PRIORITIES:
        return jsonify({"error": "Invalid priority, allowed: low, medium, high"}), 400

    # 👉 NEU: due_date als String (ISO) aus dem JSON
    due_date_str = data.get("due_date")
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.fromisoformat(due_date_str)
        except ValueError:
            return jsonify({"error": "due_date must be ISO format, e.g. 2025-11-30T18:00:00"}), 400

    task = Task(
        title=data["title"],
        description=data.get("description", ""),
        status=status,
        priority=priority,
        due_date=due_date,              # 👈 NEU
        user_id=data["user_id"],
        category_id=data.get("category_id")
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

    if "status" in data:
        new_status = data["status"]
        if new_status not in ALLOWED_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        task.status = new_status

    if "priority" in data:
        new_priority = data["priority"].lower()
        if new_priority not in ALLOWED_PRIORITIES:
            return jsonify({"error": "Invalid priority, allowed: low, medium, high"}), 400
        task.priority = new_priority

    # 👉 NEU: due_date ändern / löschen
    if "due_date" in data:
        due_date_str = data["due_date"]
        if due_date_str in (None, "", "null"):
            task.due_date = None
        else:
            try:
                task.due_date = datetime.fromisoformat(due_date_str)
            except ValueError:
                return jsonify({"error": "due_date must be ISO format"}), 400

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
    priority_order = case(
        (Task.priority == "high", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "low", 3),
        else_=4,
    )

    tasks = (
        Task.query
        .filter_by(category_id=category_id)
        .order_by(priority_order, Task.id.asc())
        .all()
    )

    return jsonify([t.to_dict() for t in tasks]), 200

# =======================
# BOARD ROUTE (KANNBAN)
# =======================

@app.route("/board", methods=["GET"])
def board_view():
    priority_order = case(
        (Task.priority == "high", 1),
        (Task.priority == "medium", 2),
        (Task.priority == "low", 3),
        else_=4,
    )

    tasks = (
        Task.query
        .order_by(priority_order, Task.id.asc())
        .all()
    )

    board = {
        "to_do": [],
        "in_progress": [],
        "done": []
    }

    for t in tasks:
        if t.status == "To Do":
            board["to_do"].append(t.to_dict())
        elif t.status == "In Progress":
            board["in_progress"].append(t.to_dict())
        elif t.status == "Done":
            board["done"].append(t.to_dict())

    return jsonify(board), 200

# =======================
# NOTIFICATIONS
# =======================

@app.route("/notifications", methods=["GET"])
def get_notifications():
    """
    Benachrichtigungen:
    - danger: Task ist überfällig
    - warning: High-Priority-Task mit Deadline in den nächsten 24h
    - info: High-Priority-Task ohne dringende Deadline
    Optional: ?user_id=1 für user-spezifische Notifications.
    """

    user_id = request.args.get("user_id", type=int)

    now = datetime.now()
    soon_threshold = now + timedelta(days=1)   # 👉 24 Stunden

    # Nur Tasks, die nicht erledigt sind
    query = Task.query.filter(Task.status != "Done")

    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    tasks = query.all()

    notifications = []

    for t in tasks:
        notif_type = None
        message = None

        # 1) ÜBERFÄLLIG → danger
        if t.due_date and t.due_date < now:
            notif_type = "danger"
            message = f"Task '{t.title}' ist überfällig."

        # 2) HIGH + DEADLINE IN 24H → warning
        elif (
            t.due_date
            and now <= t.due_date <= soon_threshold
            and t.priority == "high"
        ):
            notif_type = "warning"
            message = f"High Priority Task '{t.title}' hat eine Deadline in weniger als 24 Stunden."

        # 3) HIGH, aber noch nicht dringend → info
        elif t.priority == "high":
            notif_type = "info"
            message = f"High Priority Task '{t.title}' ist noch offen."

        if notif_type:
            notifications.append({
                "task": t.to_dict(),
                "type": notif_type,
                "message": message,
            })

    return jsonify(notifications), 200

# =======================
# Datenbank erstellen und App starten
# =======================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)