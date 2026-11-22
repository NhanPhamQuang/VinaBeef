"""Check the no-build browser interface is actually served by FastAPI."""
from pathlib import Path

def test_static_vanilla_frontend(client):
    for route in ("/", "/field"):
        result = client.get(route)
        assert result.status_code == 200
        assert "text/html" in result.headers["content-type"]
        assert "/static/assets/app.js" in result.text
        assert "/static/assets/styles.css" in result.text
        assert "react" not in result.text.lower()

    js = client.get("/static/assets/app.js")
    css = client.get("/static/assets/styles.css")
    assert js.status_code == css.status_code == 200
    assert "indexedDB" in js.text
    assert "#182232" in css.text
    assert "ReactDOM" not in js.text
    assert "import React" not in js.text
