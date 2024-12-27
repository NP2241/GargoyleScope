from flask import Flask, request, render_template, jsonify
from app import query_gdelt

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    results = query_gdelt(
        data['keyword'],
        data['startDate'],
        data['endDate']
    )
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True) 