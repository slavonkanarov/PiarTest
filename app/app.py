import datetime
from flask import Flask, render_template, redirect, request, session
from flask_sqlalchemy import SQLAlchemy
import config
import secrets

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_CONNECTION_URI
app.config['SECRET_KEY'] = secrets.token_hex()

db = SQLAlchemy(app)

tag_note = db.Table('tag_note',
                    db.Column('tag_id', db.Integer, db.ForeignKey('Tags.id'), primary_key=True),
                    db.Column('note_id', db.Integer, db.ForeignKey('Notes.id'), primary_key=True)
                    )


class Notes(db.Model):
    __tablename__ = 'Notes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), default="New Note")
    content = db.Column(db.Text, default="")
    last_modified = db.Column(db.DateTime, default=datetime.datetime.now())
    tags = db.relationship('Tags', secondary=tag_note, backref=db.backref('Notes', lazy=True))


class Tags(db.Model):
    __tablename__ = 'Tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="")
    notes = db.relationship('Notes', secondary=tag_note, backref=db.backref('Tags', lazy=True))


@app.route("/", methods=["GET"])
def home():
    if 'sort_by_name' not in session:
        session['sort_by_name'] = False
    if 'sort_by_time' not in session:
        session['sort_by_time'] = False
    if 'search_tag' not in session:
        session['search_tag'] = []
    if 'search_text' not in session:
        session['search_text'] = ""
    session.update()
    order = []
    if session['sort_by_name']:
        order.append(Notes.name)
    if session['sort_by_time']:
        order.append(Notes.last_modified.desc())

    all_note = db.session.query(Notes). \
        filter((Notes.tags.any(Tags.id.in_(session['search_tag'])) if len(session['search_tag']) else True)). \
        filter(Notes.content.like(f"%{session['search_text']}%")). \
        order_by(*order). \
        all()

    return render_template("main.html", notes=all_note, tags=Tags.query.all(),
                           search_tag=db.session.query(Tags).filter(Tags.id.in_(session['search_tag'])).all(),
                           search_text=session['search_text'],
                           sort_by_name=session['sort_by_name'], sort_by_time=session['sort_by_time'])


@app.route("/note/<int:note_id>/", methods=["GET", "POST"])
def note(note_id):
    if request.method == "POST":
        note = Notes.query.get(note_id)
        note.name = request.form["name"]
        note.content = request.form["content"]
        note.last_modified = datetime.datetime.now()
        db.session.commit()
        return redirect(f"/note/{note_id}")
    else:
        return render_template("note.html", note=Notes.query.get(note_id), tags=Tags.query.all())


@app.route("/deleteNote/<int:note_id>/", methods=["GET", "POST"])
def delete_note(note_id):
    Notes.query.filter_by(id=note_id).delete()
    db.session.commit()
    return redirect(f"/")


@app.route("/createNote/", methods=["GET", "POST"])
def create_note():
    db.session.add(Notes())
    db.session.commit()
    return redirect(f"/")


@app.route("/note/<int:note_id>/deleteTag/<int:tag_id>/", methods=["GET", "POST"])
def delete_tag_in_note(note_id, tag_id):
    note = Notes.query.get(note_id)
    tag = Tags.query.get(tag_id)
    note.tags.remove(tag)
    note.last_modified = datetime.datetime.now()
    db.session.commit()
    return redirect(f"/note/{note_id}")


@app.route("/note/<int:note_id>/addTag", methods=["GET", "POST"])
def addTag(note_id):
    note = Notes.query.get(note_id)
    tag = Tags.query.get(request.form["tag_id"])
    note.tags.append(tag)
    note.last_modified = datetime.datetime.now()
    db.session.commit()
    return redirect(f"/note/{note_id}")


@app.route("/tags/", methods=["GET"])
def tags():
    return render_template("tags.html", tags=Tags.query.all())


@app.route("/tag/<int:tag_id>/", methods=["GET", "POST"])
def tag(tag_id):
    if not request.form["name"] or request.form["name"] == "":
        return redirect(f"/tags")
    tag = Tags.query.get(tag_id)
    tag.name = request.form["name"]
    db.session.commit()
    return redirect(f"/tags")


@app.route("/deleteTag/<int:tag_id>/", methods=["GET", "POST"])
def delete_tag(tag_id):
    Tags.query.filter_by(id=tag_id).delete()
    db.session.commit()
    return redirect(f"/tags")


@app.route("/createTag/", methods=["GET", "POST"])
def create_tag():
    if not request.form['name']:
        return redirect(f"/tags")

    db.session.add(Tags(name=request.form['name']))
    db.session.commit()
    return redirect(f"/tags")


@app.route("/addSearchTag/", methods=["GET", "POST"])
def add_search_tag():
    r = int(request.form["tag_id"])
    if 'search_tag' in session:
        if r not in session['search_tag']:
            session['search_tag'].append(r)
    else:
        session['search_tag'] = [r]
    session.update()
    return redirect(f"/")


@app.route("/deleteSearchTag/<int:tag_id>/", methods=["GET", "POST"])
def delete_search_tag(tag_id):
    session['search_tag'].remove(tag_id)
    session.update()
    return redirect(f"/")


@app.route("/setSearchText/", methods=["GET", "POST"])
def set_search_text():
    session['search_text'] = request.form['text']
    session.update()
    return redirect(f"/")


@app.route("/setSortParams/", methods=["GET", "POST"])
def set_sort_params():
    if request.form.get("sort_by_name"):
        session['sort_by_name'] = True
    else:
        session['sort_by_name'] = False

    if request.form.get("sort_by_time"):
        session['sort_by_time'] = True
    else:
        session['sort_by_time'] = False
    session.update()
    return redirect(f"/")


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, host="0.0.0.0")
