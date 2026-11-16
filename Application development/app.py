from flask import Flask

app = Flask(__name__)

HOME_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proyecto SRE</title>
    <style>
        body {
            margin: 0;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
            color: #ffffff;
        }
        .card {
            text-align: center;
            padding: 3rem 4rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 { margin: 0 0 0.5rem; font-size: 2.5rem; }
        p { margin: 0; font-size: 1.4rem; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Proyecto SRE</h1>
        <p>Milena Quesada Bruno</p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return HOME_PAGE


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
