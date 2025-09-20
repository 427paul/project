from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 데이터베이스 설정
# username에는 생성한 사용자 계정명 입력
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask_user:password@localhost/flask_todo_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy 객체 생성
db = SQLAlchemy(app)

# 모델 정의
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    def __repr__(self):
        return f'<Todo {self.title}>'

@app.route('/')
def goto():
    return render_template('frontend.html')

@app.route('/todoapp')
def page():
    return render_template('frontend.html')


@app.route('/hi')
def hi():
    return"hi"


#crud 기능 넣는 위치

#Create(생성)
@app.route('/todo', methods=['POST'])
def add_todo():
    data = request.json
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    new_todo = Todo(
        title=data['title'],
        description=data.get('description', '') )
    db.session.add(new_todo)
    db.session.commit()

    return jsonify({
        'id': new_todo.id,
        'title': new_todo.title,
        'description': new_todo.description,
        'completed': new_todo.completed,
        'created_at': new_todo.created_at
    }), 201

# Read(읽기)
@app.route('/todos', methods=['GET']) 
def get_todos():
    todos = Todo.query.all() 
    return jsonify([
    {
        'id': todo.id, 
        'title': todo.title,
        'description': todo.description,
        'completed': todo.completed, 
        'created_at': todo.created_at
    } for todo in todos
    ])

# Update(갱신)
@app.route('/todo/<int:id>', methods=['PUT'])
def update_todo(id):
    todo = Todo.query.get_or_404(id)
    data = request.json
    todo.title = data.get('title', todo.title)
    todo.description = data.get('description', todo.description)
    todo.completed = data.get('completed', todo.completed)
    db.session.commit()
    return jsonify({
        'id': todo.id,
        'title': todo.title,
        'description': todo.description,
        'completed': todo.completed,
        'created_at': todo.created_at
    })

#Delete(삭제)
@app.route('/todo/<int:id>', methods=['DELETE'])
def delete_todo(id):
    todo = Todo.query.get_or_404(id) 
    db.session.delete(todo)
    db.session.commit()
    return jsonify({'message': 'Todo deleted successfully'}), 200

    
# 필터링
@app.route('/todos/completed', methods=['GET']) 
def get_completed_todos():
    completed_todos = Todo.query.filter_by(completed=True).all() 
    return jsonify([
    {
        'id': todo.id, 
        'title': todo.title,
        'description': todo.description,
        'created_at': todo.created_at
    } for todo in completed_todos
])

# 정렬
@app.route('/todos/sorted', methods=['GET']) 
def get_sorted_todos():
    sorted_todos = Todo.query.order_by(Todo.created_at.desc()).all()
    return jsonify([
    {
        'id': todo.id, 
        'title': todo.title,
        'description': todo.description,
        'completed': todo.completed,
        'created_at': todo.created_at
    } for todo in sorted_todos
])

# 페이지네이션
@app.route('/todos/paginated', methods=['GET']) 
def get_paginated_todos():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    paginated_todos = Todo.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({ 
    'todos': [
        {
            'id': todo.id, 
            'title': todo.title,
            'description': todo.description, 
            'completed': todo.completed, 
            'created_at': todo.created_at
        } for todo in paginated_todos.items
    ],
    'total': paginated_todos.total,
    'pages': paginated_todos.pages, 
    'current_page': page
})

# 복합쿼리
# @app.route('/todos/search', methods=['GET'])
# def search_todos():
#     keyword = request.args.get('keyword', '')
#     todos = Todo.query.filter(
#         Todo.title.like(f'%{keyword}%'),
#         Todo.completed == False
#     ).all()
#     return jsonify([
#         {
#             'id': todo.id, 
#             'title': todo.title,
#             'description': todo.description,
#             'completed': todo.completed, 
#             'created_at': todo.created_at
#         } for todo in todos
#     ])
@app.route('/todos/search', methods=['GET'])
def search_todos():
    keyword = request.args.get('keyword', '')

    if not keyword:
        return jsonify([]), 200

    # title이 keyword와 정확히 일치하는 항목만 반환
    todos = Todo.query.filter(Todo.title == keyword).all()

    return jsonify([
        {
            'id': todo.id, 
            'title': todo.title,
            'description': todo.description, 
            'completed': todo.completed, 
            'created_at': todo.created_at
        } for todo in todos
    ])


@app.route('/delete-todos', methods=['POST'])
def delete_todos():
    data = request.json
    ids_to_delete = data.get('ids', [])
    
    if not ids_to_delete:
        return jsonify({'error': 'No IDs provided'}), 400

    # 선택된 항목을 삭제
    Todo.query.filter(Todo.id.in_(ids_to_delete)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({'message': 'Selected todos deleted successfully'}), 200

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)