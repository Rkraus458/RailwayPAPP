from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Python Practice App is live on Railway!"

if __name__ == "__main__":
    # Railway sets a PORT environment variable; we must use it
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)