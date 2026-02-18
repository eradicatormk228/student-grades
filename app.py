from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Функция для текущей даты в шаблонах
@app.context_processor
def utility_processor():
    return {'now': datetime.now}

DATA_FILE = 'groups.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/groups')
def groups():
    data = load_data()
    return render_template('groups.html', groups=data)

@app.route('/groups/create', methods=['POST'])
def create_group():
    data = load_data()
    name = request.form.get('name')
    
    if not name:
        flash('Название группы не может быть пустым', 'danger')
        return redirect(url_for('groups'))
    
    if name in data:
        flash('Группа с таким названием уже существует', 'danger')
        return redirect(url_for('groups'))
    
    data[name] = {
        'subjects': [],
        'students': {},
        'lessons': [],
        'created': datetime.now().strftime('%d.%m.%Y %H:%M')
    }
    save_data(data)
    flash(f'Группа "{name}" создана', 'success')
    return redirect(url_for('groups'))

@app.route('/groups/<name>')
def group(name):
    data = load_data()
    if name not in data:
        flash('Группа не найдена', 'danger')
        return redirect(url_for('groups'))
    return render_template('group.html', group_name=name, group=data[name])

@app.route('/groups/<name>/add_subject', methods=['POST'])
def add_subject(name):
    data = load_data()
    subject = request.form.get('subject')
    if subject and subject not in data[name]['subjects']:
        data[name]['subjects'].append(subject)
        save_data(data)
        flash(f'Предмет "{subject}" добавлен', 'success')
    return redirect(url_for('group', name=name))

@app.route('/groups/<name>/delete_subject/<subject>')
def delete_subject(name, subject):
    data = load_data()
    if subject in data[name]['subjects']:
        data[name]['subjects'].remove(subject)
        save_data(data)
        flash(f'Предмет "{subject}" удалён', 'success')
    return redirect(url_for('group', name=name))

@app.route('/groups/<name>/add_student', methods=['POST'])
def add_student(name):
    data = load_data()
    student_name = request.form.get('student_name')
    if student_name:
        students = data[name]['students']
        next_id = 1
        if students:
            next_id = max([int(id) for id in students.keys()]) + 1
        students[str(next_id)] = {
            'name': student_name,
            'date_added': datetime.now().strftime('%d.%m.%Y %H:%M')
        }
        save_data(data)
        flash(f'Студент {student_name} добавлен', 'success')
    return redirect(url_for('group', name=name))

@app.route('/groups/<name>/delete_student/<student_id>')
def delete_student(name, student_id):
    data = load_data()
    if student_id in data[name]['students']:
        student_name = data[name]['students'][student_id]['name']
        del data[name]['students'][student_id]
        save_data(data)
        flash(f'Студент {student_name} удалён', 'success')
    return redirect(url_for('group', name=name))

@app.route('/groups/<name>/lesson', methods=['GET', 'POST'])
def lesson(name):
    data = load_data()
    if request.method == 'POST':
        subject = request.form.get('subject')
        date = request.form.get('date') or datetime.now().strftime('%d.%m.%Y')
        topic = request.form.get('topic')
        homework = request.form.get('homework')
        
        grades = {}
        for key, value in request.form.items():
            if key.startswith('grades_'):
                student_id = key.replace('grades_', '')
                if value.strip():
                    grade_list = []
                    for g in value.split():
                        try:
                            grade = float(g.replace(',', '.'))
                            if 2 <= grade <= 5:
                                grade_list.append(grade)
                        except:
                            pass
                    if grade_list:
                        grades[student_id] = grade_list
        
        lesson_data = {
            'date': date,
            'subject': subject,
            'topic': topic,
            'homework': homework,
            'grades': grades
        }
        
        data[name]['lessons'].append(lesson_data)
        save_data(data)
        flash('Урок проведён', 'success')
        return redirect(url_for('group', name=name))
    
    return render_template('lesson.html', group_name=name, group=data[name])

@app.route('/groups/<name>/journal')
def journal(name):
    data = load_data()
    lessons = sorted(data[name]['lessons'], key=lambda x: x['date'], reverse=True)
    return render_template('journal.html', group_name=name, lessons=lessons, students=data[name]['students'])

@app.route('/groups/<name>/student/<student_id>')
def student_grades(name, student_id):
    data = load_data()
    student = data[name]['students'][student_id]
    lessons = data[name]['lessons']
    
    subjects_grades = {}
    for lesson in lessons:
        if student_id in lesson['grades']:
            subject = lesson['subject']
            if subject not in subjects_grades:
                subjects_grades[subject] = []
            for grade in lesson['grades'][student_id]:
                subjects_grades[subject].append({
                    'date': lesson['date'],
                    'grade': grade
                })
    
    averages = {}
    for subject, grades in subjects_grades.items():
        avg = sum(g['grade'] for g in grades) / len(grades)
        averages[subject] = round(avg, 2)
    
    return render_template('student.html', group_name=name, student=student, 
                         subjects_grades=subjects_grades, averages=averages)

@app.route('/groups/<name>/statistics')
def statistics(name):
    data = load_data()
    students = data[name]['students']
    lessons = data[name]['lessons']
    
    student_averages = []
    for student_id, student in students.items():
        grades = []
        for lesson in lessons:
            if student_id in lesson['grades']:
                grades.extend(lesson['grades'][student_id])
        if grades:
            avg = sum(grades) / len(grades)
            student_averages.append({'name': student['name'], 'avg': round(avg, 2)})
    
    student_averages.sort(key=lambda x: x['avg'], reverse=True)
    
    total = len(student_averages)
    excellent = len([s for s in student_averages if s['avg'] >= 4.5])
    good = len([s for s in student_averages if 3.5 <= s['avg'] < 4.5])
    satisfactory = len([s for s in student_averages if 2.5 <= s['avg'] < 3.5])
    poor = len([s for s in student_averages if s['avg'] < 2.5])
    
    return render_template('statistics.html', group_name=name,
                         students_count=len(students),
                         lessons_count=len(lessons),
                         student_averages=student_averages,
                         excellent=excellent, good=good,
                         satisfactory=satisfactory, poor=poor,
                         total_with_grades=total)

@app.route('/groups/<name>/delete')
def delete_group(name):
    data = load_data()
    del data[name]
    save_data(data)
    flash(f'Группа "{name}" удалена', 'success')
    return redirect(url_for('groups'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
