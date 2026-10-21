from html.parser import HTMLParser
from pathlib import Path


WEB_DIR = Path(__file__).resolve().parents[2] / "web"


class AppMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = False
        self.heading = False
        self.status = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.title |= tag == "title"
        self.heading |= tag == "h1"
        self.status |= attributes.get("id") == "app-status"


def test_static_app_has_accessible_spanish_document():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert '<html lang="es">' in html
    parser = AppMarkupParser()
    parser.feed(html)
    assert parser.title
    assert parser.heading
    assert parser.status


def test_static_app_has_expected_content():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "DevOps Lab" in html
    assert "Aplicación operativa" in html
    assert "Kubernetes" in html


def test_nginx_exposes_health_endpoint():
    nginx_conf = (WEB_DIR / "nginx.conf").read_text(encoding="utf-8")
    assert "location = /health" in nginx_conf
    assert 'return 200 "ok\\n"' in nginx_conf
