import json

from db import db
from db import Course, User, Assignment, Submission
from flask import Flask, request
import boto3
import os

db_filename = "cms.db"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % db_filename
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db.init_app(app)
with app.app_context():
    db.create_all()

@app.route('/')
def hello_world():
    return os.environ['GOOGLE_CLIENT_ID'], 200

@app.route('/api/courses/')
def get_all_courses():
    courses = Course.query.all()
    res = {'success': True, 'data': [c.serialize_no_users() for c in courses]}
    return json.dumps(res), 200

@app.route('/api/courses/', methods=['POST'])
def create_course():
    post_body = json.loads(request.data)
    code = post_body.get('code')
    name = post_body.get('name')
    course = Course(
        code=code,
        name=name,
        assignments=[],
        users=[]
    )
    db.session.add(course)
    db.session.commit()
    return json.dumps({'success': True, 'data': course.serialize()}), 201

@app.route('/api/course/<int:course_id>/')
def get_course(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return json.dumps({'success': False, 'error': 'Course not found'}), 404
    return json.dumps({'success': True, 'data': course.serialize()}), 200

@app.route('/api/users/', methods=['POST'])
def create_user():
    post_body = json.loads(request.data)
    user = User(
        name=post_body.get('name'),
        netid=post_body.get('netid')
    )
    db.session.add(user)
    db.session.commit()
    return json.dumps({'success': True, 'data': user.serialize()}), 201

@app.route('/api/user/<int:user_id>/')
def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    return json.dumps({'success': True, 'data': user.serialize()}), 200

# tasks and categories
@app.route('/api/course/<int:course_id>/add/', methods=['POST'])
def add_user_to_course(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return json.dumps({'success': False, 'error': 'Course not found'}), 404
    post_body = json.loads(request.data)
    user = User.query.filter_by(id=post_body.get('user_id')).first()
    if not user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    type = post_body.get('type', 'student')
    if type == 'student':
        course.students.append(user)
    else:
        course.instructors.append(user)
    db.session.add(user)
    db.session.commit()
    return json.dumps({'success': True, 'data': course.serialize()})

# Tasks and subtasks
@app.route('/api/course/<int:course_id>/assignment/', methods=['POST'])
def create_assignment_for_course(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return json.dumps({'success': False, 'error': 'Course not found'}), 404
    post_body = json.loads(request.data)
    assignment = Assignment(
        title=post_body.get('title'),
        due_date=post_body.get('due_date'),
    )
    course.assignments.append(assignment)
    db.session.add(assignment)
    db.session.commit()
    res = assignment.serialize()
    course = course.serialize_no_users()
    del course['assignments']
    res['course'] = course
    return json.dumps({'success': True, 'data': res})

@app.route('/api/course/<course_id>/drop/', methods=['POST'])
def drop_user_from_course(course_id):
    course = Course.query.filter_by(id=course_id).first()
    if not course:
        return json.dumps({'success': False, 'error': 'Course not found'}), 404
    post_body = json.loads(request.data)
    user = User.query.filter_by(id=post_body.get('user_id')).first()
    if not user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    if user not in course.students:
        return json.dumps({'success': False, 'error': 'User has not been added to this course'}), 404
    course.students.remove(user)
    db.session.commit()
    return json.dumps({'success': True, 'data': user.serialize()})

@app.route('/api/assignment/<assignment_id>/', methods=['POST'])
def update_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id).first()
    if not assignment:
        return json.dumps({'success': False, 'error': 'Assignment not found'}), 404
    post_body = json.loads(request.data)
    title = post_body.get('title', assignment.title)
    due_date = post_body.get('due_date', assignment.due_date)
    assignment.title = title
    assignment.due_date = due_date
    db.session.commit()
    return json.dumps({'success': True, 'data': assignment.serialize()})

@app.route('/api/assignment/<assignment_id>/submit/', methods=['POST'])
def submit_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id).first()
    if not assignment:
        return json.dumps({'success': False, 'error': 'Assignment not found'}), 404
    user_id = request.form.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return json.dumps({'success': False, 'error': 'User not found'}), 404
    client = boto3.client('s3')
    file = request.files.get('content')
    bucket_name = 'cmsproject-bucket'
    file_name = user.name + '/' + file.filename
    client.put_object(Body=file, Bucket=bucket_name, Key=file_name)
    submission = Submission(
        content=client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': file_name}, ExpiresIn=3600)
    )
    course = Course.query.filter_by(id=assignment.course_id).first()
    if user not in course.students:
        return json.dumps({'success': False, 'error': 'User does not have this assignment'}), 400
    assignment.submissions.append(submission)
    db.session.add(submission)
    db.session.commit()
    return json.dumps({'success': True, 'data': submission.serialize()})

@app.route('/api/assignment/<assignment_id>/grade/', methods=['POST'])
def grade_assignment(assignment_id):
    assignment = Assignment.query.filter_by(id=assignment_id).first()
    if not assignment:
        return json.dumps({'success': False, 'error': 'Assignment not found'}), 404
    post_body = json.loads(request.data)
    submission_id = post_body.get('submission_id')
    submission = Submission.query.filter_by(id=submission_id).first()
    if not submission:
        return json.dumps({'success': False, 'error': 'Submission not found'}), 404
    if submission not in assignment.submissions:
        return json.dumps({'success': False, 'error': 'Submission does not match this assignment'}), 404
    score = post_body.get('score', submission.score)
    submission.score = score
    db.session.commit()
    return json.dumps({'success': True, 'data': submission.serialize()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
