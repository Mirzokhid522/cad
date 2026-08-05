import os
import requests
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/score', methods=['GET'])
def get_macro_score():
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, headers=HEADERS, timeout=5)
        
        if response.status_code != 200:
            print(f"Notion API Error: {response.status_code} - {response.text}")
            return jsonify({"error": f"Notion API error {response.status_code}", "score": 0.0, "status": "Error"}), 500

        data = response.json()
        results = data.get("results", [])
        
        total_score = 0.0
        count = 0
        bias_statuses = []

        for page in results:
            props = page.get("properties", {})
            
            # 1. Fetch and parse Score
            score_prop = props.get("Score", {})
            p_type = score_prop.get("type")
            
            val = None
            if p_type == "rollup":
                val = score_prop.get("rollup", {}).get("number")
            elif p_type == "number":
                val = score_prop.get("number")
            elif p_type == "formula":
                val = score_prop.get("formula", {}).get("number")

            if val is not None:
                total_score += float(val)
                count += 1

            # 2. Fetch and parse Bias
            bias_prop = props.get("Bias", {})
            b_type = bias_prop.get("type")
            
            bias_val = None
            if b_type == "formula":
                formula_data = bias_prop.get("formula", {})
                f_sub_type = formula_data.get("type")
                bias_val = formula_data.get(f_sub_type)
            elif b_type == "select":
                select_data = bias_prop.get("select")
                if select_data:
                    bias_val = select_data.get("name")
            elif b_type == "rich_text":
                texts = bias_prop.get("rich_text", [])
                bias_val = texts[0]["plain_text"] if texts else None
            elif b_type == "string":
                bias_val = bias_prop.get("string")

            if bias_val is not None:
                bias_statuses.append(str(bias_val))

        score = round(total_score, 4) if count > 0 else 0.0
        
        # Strictly use the fetched Notion Bias, or default to "Unknown" if not found
        status = bias_statuses[0] if bias_statuses else "Unknown"

        return jsonify({
            "score": score,
            "status": status
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e), "score": 0.0, "status": "Error"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)