from flask import Flask, request, redirect, url_for, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'todos.db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # Для старых версий Python
    
def get_moscow_time():
    """Возвращает текущее время по Москве"""
    try:
        return datetime.now(ZoneInfo("Europe/Moscow"))
    except Exception:
        # Для старых версий Python с pytz
        import pytz
        return datetime.now(pytz.timezone("Europe/Moscow"))

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: get_moscow_time(), nullable=False)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)  # Добавляем поле для времени изменения
    is_edited = db.Column(db.Boolean, default=False)  # Флаг редактирования
        

def check_and_upgrade_db():
    with app.app_context():
        # Проверяем существование таблицы
        inspector = db.inspect(db.engine)
        if 'todo' not in inspector.get_table_names():
            db.create_all()
            return
        
        # Проверяем существование колонок
        columns = [c['name'] for c in inspector.get_columns('todo')]
        
        # Добавляем недостающие колонки
        with db.engine.connect() as conn:
            if 'updated_at' not in columns:
                conn.execute(text('ALTER TABLE todo ADD COLUMN updated_at DATETIME'))
            if 'is_edited' not in columns:
                conn.execute(text('ALTER TABLE todo ADD COLUMN is_edited BOOLEAN DEFAULT FALSE'))
            conn.commit()
    
@app.route("/")
def index():
    return redirect(url_for("active_tasks"))    
    
@app.route("/active", methods=["GET", "POST"])
def active_tasks():
    if request.method == "POST":
        task = request.form.get("task")
        if task:
            new_todo = Todo(task=task)
            db.session.add(new_todo)
            db.session.commit()
        return redirect(url_for("active_tasks"))
    
    active = Todo.query.filter_by(completed=False).order_by(Todo.created_at.desc()).all()
    return render_template("index.html", todos=active, active_tab='active')

@app.route("/completed", methods=["GET"])  # Убираем POST здесь
def completed_tasks():
    completed = Todo.query.filter_by(completed=True).order_by(Todo.completed_at.desc()).all()
    return render_template("index.html", todos=completed, active_tab='completed')  

@app.route('/complete/<int:id>')
def complete_task(id):
    todo = Todo.query.get_or_404(id)
    if not todo.completed:
        todo.completed = True
        todo.completed_at = get_moscow_time()
        db.session.commit()
    return jsonify({
        'status': 'success',
        'completed': True,
        'completed_at': todo.completed_at.strftime('%d.%m.%Y %H:%M')
    })

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    todo = Todo.query.get_or_404(id)
    if todo.completed:
        return jsonify({'status': 'error', 'message': 'Нельзя редактировать завершенную задачу'}), 403
    
    new_task = request.form.get('task', '').strip()
    if not new_task:
        return jsonify({'status': 'error', 'message': 'Текст задачи не может быть пустым'}), 400
        
    if new_task != todo.task:
        todo.task = new_task
        now = get_moscow_time()
        todo.updated_at = now
        todo.is_edited = True
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'updated_at': now.astimezone(ZoneInfo("Europe/Moscow")).strftime('%d.%m.%Y %H:%M'),
            'is_edited': True,
            'new_text': new_task
        })
    
    return jsonify({'status': 'no_changes'})

@app.route("/delete/<int:id>")
def delete(id):
    todo = Todo.query.get(id)
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route("/toggle/<int:id>")
def toggle(id):
    todo = Todo.query.get_or_404(id)
    todo.completed = True
    todo.completed_at = get_moscow_time() if todo.completed else None
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route("/reactivate/<int:id>")
def reactivate_task(id):
    """Возвращает задачу в активные"""
    todo = Todo.query.get_or_404(id)
    if todo.completed:
        todo.completed = False
        todo.completed_at = None
        db.session.commit()
    return jsonify({
        'status': 'success',
        'completed': False
    })

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def forbidden_error(error):
    return render_template('404.html'), 404

@app.template_filter('format_date')
def format_date_filter(dt, format='%d.%m.%Y %H:%M'):
    if dt is None:
        return "не указано"
    return dt.strftime(format)

if __name__ == "__main__":
    with app.app_context():
        check_and_upgrade_db()
        db.create_all()  # Дополнительная проверка при запуске
    app.run(host="0.0.0.0", port=5000, debug=True)