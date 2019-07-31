# db driver here
import pypyodbc

# for local file/folders path
import os
import time
import io
import csv
import pandas as pd

# Flask utilities here
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, make_response
#from data import Articles

#WTF Form fields
from wtforms import Form, StringField, TextAreaField, PasswordField, validators

# Secure password
from passlib.hash import sha256_crypt

# Flask snippets for decorations
from functools import wraps

# File Upload utility
from werkzeug.utils import secure_filename

app = Flask(__name__)

# SQL Server configuration here
connection = pypyodbc.connect('Driver={SQL Server};Server=DESKTOP-MANISH;Database=MyFlaskApp;Integrated Security=true;')
# connection = pypyodbc.connect('Driver={SQL Server};Server=DESKTOP-MANISH;Database=MyFlaskApp;uid=sa;pwd=mail_123')
# Creating Cursor
#app.config['SQL_CURSORCLASS'] = 'DictCursor'

# Load data of Articles from data
# Articles = Articles()

# index page
@app.route('/')
def index():
    return render_template('home.html')

# about page
@app.route('/about')
def about():
    return render_template('about.html')

# articles list page
@app.route('/articles')
def articles():
    # Read the files from the uploads directory and list them in table
    print('File         :', __file__)
    print('Access time  :', time.ctime(os.path.getatime(__file__)))
    print('Modified time:', time.ctime(os.path.getmtime(__file__)))
    print('Change time  :', time.ctime(os.path.getctime(__file__)))
    print('Size         :', os.path.getsize(__file__))
    return render_template('articles.html')


# single article page
@app.route('/article/<string:id>')
def article(id):
    # create cursor
    cursor = connection.cursor()
    # execute the query
    resultCount = cursor.execute(" SELECT * FROM Posts WHERE ID=?",[id]).rowcount
    print(resultCount)
    article  = cursor.fetchone()

    return render_template('article.html', article = article)

# User Register class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('UserName', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired()
        ,validators.EqualTo('confirm', message='Password do not match')
        ])
    confirm = PasswordField('Confirm Password') 

# user Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        #do something here
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        cursor = connection.cursor()  
        # execute the query
        cursor.execute("INSERT INTO [dbo].[Users] ([Name], [UserName],[Password],[Email])  VALUES (?, ?, ?, ?)",(name, username, password, email))
        # commit to DB
        cursor.commit()
        # close DB connection
        ##connection.close()

        flash('Thanks '+name+' for registering the application', 'info')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        # get form fields
        username = request.form['username']
        password_candidate = request.form['password']
        #app.logger.info('UserName: '+username + '  ; Password: ' +password_candidate)

        # create cursor
        cursor = connection.cursor()
        # execute the query #'"+username+"'"        
        result = cursor.execute("SELECT * FROM Users WHERE UserName=?",[username])
        #print(result)

        if result is not None:
            data = cursor.fetchone()
            #print(data)
            if data is not None:
                password = data[2]
                #app.logger.info('DB Password: '+ password)
                #Compare the password
                if sha256_crypt.verify(password_candidate, password):
                    #app.logger.info('Password Matched')
                    session['logged_in'] = True
                    session['username'] = username
                    flash('Welcome '+username, 'info')
                    return redirect( url_for('dashboard'))
                else:
                    flash('Either username or password does not match.', 'danger')
            else:
                flash('Specified user credential does not exist with the application', 'danger')
                # finally close the connection here
                cursor.close()
        else:
            #app.logger.info('No User')
            flash('Are you missing password or username is not correct', 'danger')
    
    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized access, please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# logout page
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are logged out of application.', 'info')
    return redirect( url_for('login'))

# dashboard page
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    cursor = connection.cursor()
    # execute the query
    resultCount = cursor.execute(" SELECT * FROM Posts ").rowcount
    print(resultCount)
    if resultCount < 0:
        print('articles found')
        articles = row_as_dict(cursor)
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    # close the connection
    cursor.close()

# User Article form class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    content = TextAreaField('Content', [validators.Length(min=30)])

# Add Article page
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data
        # create cursor
        cursor = connection.cursor()  
        # execute the query
        cursor.execute("INSERT INTO [dbo].[Posts] ([Title],[Content],[Author],[Tags],[Status])  VALUES (?, ?, ?, ?, ?)",(title, content, session['username'], 'Technical', 'Publish'))
        # commit to DB
        cursor.commit()
        # close DB connection
        cursor.close()
        flash('Article created successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# Edit Article page
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    cursor = connection.cursor()  
    # execute the query
    cursor.execute("SELECT * FROM Posts WHERE ID=?", [id])
    article = cursor.fetchone()
    form = ArticleForm(request.form)
    # populate fields from data
    form.title.data = article[1]
    form.content.data = article[2]

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        content = request.form['content']
        print('updated title: '+title)
        print('updated content: '+content)
        # create cursor
        cursor = connection.cursor()  
        # execute the query
        cursor.execute("UPDATE Posts SET [Title]=?, [Content]=?  WHERE [ID]=?",(title, content, id))
        # commit to DB
        cursor.commit()
        # close DB connection
        cursor.close()
        flash('Article updated successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Edit Article page
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # create cursor
    cursor = connection.cursor()  
    # execute the query
    cursor.execute("DELETE FROM Posts WHERE ID=?", [id])
    # commit to DB
    cursor.commit()
    # close DB connection
    cursor.close()
    flash('Article deleted successfully', 'success')
    return redirect(url_for('dashboard'))

# File Upload page
UPLOAD_FOLDER = './static/FilesUpload'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'csv', 'xlsx', 'xls'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['MAX_CONTENT_PATH'] = 
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def transform(text_file_contents):
    return text_file_contents.replace("=", ",")

@app.route('/upload', methods=['GET', 'POST'])
@is_logged_in
def upload():
    if request.method == 'POST':
        # check if the POST request has filepart
        if 'file' not in request.files:
            flash('File not detected', 'danger')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        # actual file upload here
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            saved_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(saved_file_path)

            #Using Pandas reading file
           # df = pd.read_csv(r'D:\Projects\PythonFlaskApp\static\FilesUpload\emplyoee.csv')
           # print(df[['ID']][df.ID==1])


            # file saved on UPLOAD_FOLDER location, now read the file and print in console
            # stream = io.StringIO(filename.stream.read().decode("UTF8"), newline=None)
            with open(saved_file_path, newline='') as f:
                csv_reader = csv.reader(f)
                for row in csv_reader:
                    print(row)
            # csv_input = csv.reader(stream)
            # print("file contents: ", file_contents)
            # print(type(file_contents))
            # print(csv_input)

            # stream.seek(0)
            # result = transform(stream.read())

            # response = make_response(result)
            # response.headers["Content-Disposition"] = "attachment; filename=result.csv"
            # return response
            return redirect(url_for('upload', filename=filename))
    return render_template('articles.html')

# Convert Curson to DICT
def row_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    for row in cursor:
        yield dict(zip(columns, row))

if __name__ == '__main__':
    app.secret_key = 'myFlaskApp123'
    app.run(debug=True)
