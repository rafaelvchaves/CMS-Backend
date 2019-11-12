from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

students_courses_table = db.Table(
    'students_courses',
    db.Model.metadata,
    db.Column('course_id', db.Integer, db.ForeignKey('course.id')),
    db.Column('user_id', db.Integer,
              db.ForeignKey('user.id'))
)
instructors_courses_table = db.Table(
    'instructors_courses',
    db.Model.metadata,
    db.Column('course_id', db.Integer, db.ForeignKey('course.id')),
    db.Column('user_id', db.Integer,
              db.ForeignKey('user.id'))
)


class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    assignments = db.relationship('Assignment', cascade='delete')
    instructors = db.relationship('User', secondary=instructors_courses_table, back_populates='instructor_courses')
    students = db.relationship('User', secondary=students_courses_table, back_populates='student_courses')

    def __init__(self, **kwargs):
        self.code = kwargs.get('code')
        self.name = kwargs.get('name')
        self.assignments = []
        self.instructors = []
        self.students = []

    def serialize(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'assignments': [a.serialize() for a in self.assignments],
            'instructors': [i.serialize_no_courses() for i in self.instructors],
            'students': [s.serialize_no_courses() for s in self.students]
        }

    def serialize_no_users(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'assignments': [a.serialize() for a in self.assignments]
        }


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    netid = db.Column(db.String, nullable=False)
    instructor_courses = db.relationship('Course', secondary=instructors_courses_table, back_populates='instructors')
    student_courses = db.relationship('Course', secondary=instructors_courses_table, back_populates='students')

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.netid = kwargs.get('netid')
        self.instructor_courses = []
        self.student_courses = []

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'netid': self.netid,
            'courses': [s.serialize_no_users() for s in self.student_courses] + [i.serialize_no_users() for i in self.instructor_courses]
        }

    def serialize_no_courses(self):
        return {
            'id': self.id,
            'name': self.name,
            'netid': self.netid
        }


class Assignment(db.Model):
    __tablename__ = 'assignment'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    due_date = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    submissions = db.relationship('Submission', cascade='delete')

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.due_date = kwargs.get('due_date')
        self.submissions = []

    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'due_date': self.due_date
        }

class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String, nullable=False)
    score = db.Column(db.Integer, nullable=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)

    def __init__(self, **kwargs):
        self.content = kwargs.get('content')
        self.score = None

    def serialize(self):
        return {
            'id': self.id,
            'content': self.content,
            'score': self.score
        }
