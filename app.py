from flask import Flask, render_template

app: Flask = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/sign-up')
def sign():
    return render_template("sign-up.html")

@app.route('/log-in')
def log():
    return render_template("log-in.html")

if __name__ == '__main__':
    app.run(debug=True)