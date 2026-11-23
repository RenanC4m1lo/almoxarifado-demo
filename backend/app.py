# ============================================================
# app.py - Arquivo principal do backend
# ============================================================

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

from bootstrap_demo import inicializar_se_necessario
inicializar_se_necessario()

# Pasta do frontend (pages/css/js estaticos) - servida pelo mesmo
# processo Flask nesta versao de demonstracao, pra caber no plano
# gratuito do PythonAnywhere (so permite 1 aplicacao web por conta).
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

from routes.auth import auth_bp
from routes.usuarios import usuarios_bp
from routes.equipamentos import equipamentos_bp
from routes.fornecedores import fornecedores_bp
from routes.movimentacoes import movimentacoes_bp
from routes.alertas import alertas_bp
from routes.relatorios import relatorios_bp
from routes.unidades import unidades_bp
from routes.empresas import empresas_bp  # nova rota de empresas
from routes.tecnicos import tecnicos_bp

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)

jwt = JWTManager(app)
origens_permitidas = os.getenv("CORS_ORIGINS", "*")
if origens_permitidas == "*":
    CORS(app)
else:
    lista_origens = [o.strip() for o in origens_permitidas.split(",")]
    CORS(app, origins=lista_origens)

app.register_blueprint(auth_bp,          url_prefix="/api/auth")
app.register_blueprint(usuarios_bp,      url_prefix="/api/usuarios")
app.register_blueprint(equipamentos_bp,  url_prefix="/api/equipamentos")
app.register_blueprint(fornecedores_bp,  url_prefix="/api/fornecedores")
app.register_blueprint(movimentacoes_bp, url_prefix="/api/movimentacoes")
app.register_blueprint(alertas_bp,       url_prefix="/api/alertas")
app.register_blueprint(relatorios_bp,    url_prefix="/api/relatorios")
app.register_blueprint(unidades_bp,      url_prefix="/api/unidades")
app.register_blueprint(empresas_bp,      url_prefix="/api/empresas")  # nova rota
app.register_blueprint(tecnicos_bp,      url_prefix="/api/tecnicos")


# ============================================================
# Serve o frontend (HTML/CSS/JS) a partir do mesmo processo
# ============================================================
@app.route("/")
def raiz():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/<path:caminho>")
def arquivos_frontend(caminho):
    if os.path.isfile(os.path.join(FRONTEND_DIR, caminho)):
        return send_from_directory(FRONTEND_DIR, caminho)
    return send_from_directory(FRONTEND_DIR, "login.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)