import os
from flask import Flask, jsonify, render_template
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


@app.route("/", methods=["GET"])
def index():
  return render_template("index.html")


@app.route("/api/score", methods=["GET"])
@app.route("/api/data", methods=["GET"])
def get_score_data():
  if not NOTION_TOKEN or not DATABASE_ID:
    return (
        jsonify({
            "error": "Configuration Error",
            "details": (
                "NOTION_TOKEN or DATABASE_ID is missing from environment"
                " variables or .env file."
            ),
        }),
        500,
    )

  url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

  try:
    response = requests.post(url, headers=headers)
  except Exception as e:
    return (
        jsonify({
            "error": "Network Error",
            "details": str(e),
        }),
        500,
    )

  if response.status_code != 200:
    return (
        jsonify({
            "error": "Notion API Error",
            "status_code": response.status_code,
            "details": response.text,
        }),
        500,
    )

  try:
    data = response.json()
    results = []

    for page in data.get("results", []):
      props = page.get("properties", {})

      score_value = 0.0
      bias_value = "Bearish CAD"
      row_title = "CAD Metric"

      # 0. Extract Row Title (CAD column)
      title_prop = props.get("CAD", {})
      if title_prop.get("type") == "title":
        title_list = title_prop.get("title", [])
        if title_list:
          row_title = title_list[0].get("text", {}).get("content", "CAD Metric")

      # 1. Extract Rollup Score safely
      score_prop = props.get("Score", {})
      if score_prop.get("type") == "rollup":
        rollup_data = score_prop.get("rollup", {})
        if rollup_data.get("type") == "number":
          score_value = rollup_data.get("number", 0.0) or 0.0
        elif rollup_data.get("type") == "array":
          array_vals = rollup_data.get("array", [])
          if array_vals:
            first_val = array_vals[0]
            if "number" in first_val:
              score_value = first_val.get("number", 0.0) or 0.0

      # 2. Extract Bias formula / text value safely
      bias_prop = props.get("Bias", {})
      ptype = bias_prop.get("type")
      if ptype == "formula":
        formula_data = bias_prop.get("formula", {})
        bias_value = (
            formula_data.get("string")
            or formula_data.get("number")
            or "Bearish CAD"
        )
      elif ptype == "select":
        bias_value = bias_prop.get("select", {}).get("name") or "Bearish CAD"
      elif ptype == "rich_text":
        rt = bias_prop.get("rich_text", [])
        if rt:
          bias_value = rt[0].get("plain_text") or "Bearish CAD"

      results.append({
          "title": row_title,
          "score": score_value,
          "bias": str(bias_value),
          "currency": "CAD",
      })

    if not results:
      results = [{
          "title": "CAD Metric",
          "score": 0.0,
          "bias": "Bearish CAD",
          "currency": "CAD",
      }]

    return jsonify(results)

  except Exception as e:
    print("Parsing Error Traceback:", str(e))
    return (
        jsonify({
            "error": "Parsing Error",
            "details": str(e),
        }),
        500,
    )


if __name__ == "__main__":
  app.run(debug=True, port=5000)