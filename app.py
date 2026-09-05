from flask import Flask


app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>SupportPilot AI</h1><p>Flask is running.</p>"


if __name__ == "__main__":
    app.run(port=8000, debug=True)
