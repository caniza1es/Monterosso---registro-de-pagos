from mongoengine import Document,StringField

class Student(Document):
    nombre = StringField(required=True)
    grado = StringField(required=True)
