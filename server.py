import threading
import requests
import folium
from flask import Flask, render_template_string, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
import webbrowser

# --- 1. CONFIGURAÇÃO DO SERVIDOR E BANCO DE DADOS ---
app = Flask(__name__)
app.secret_key = 'dash_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oficina_dash.db'
db = SQLAlchemy(app)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80))
    preco = db.Column(db.Float)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20)) # 'Pendente', 'Concluido'

# --- 2. ROTAS FLASK (DASHBOARD E MAPA) ---

@app.route('/')
def dashboard():
    # Estatísticas para o Dashboard
    total_produtos = Produto.query.count()
    servicos_pendentes = Servico.query.filter_by(status='Pendente').count()
    valor_estoque = db.session.query(db.func.sum(Produto.preco)).scalar() or 0
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>Dashboard Oficina Pro</title>
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark p-3">
            <span class="navbar-brand">📊 Dash Oficina Pro</span>
            <a href="/mapa" class="btn btn-outline-warning">Ver Localização</a>
        </nav>
        <div class="container mt-4">
            <div class="row g-3 mb-4">
                <div class="col-4">
                    <div class="card bg-primary text-white p-3 text-center">
                        <h6>Produtos</h6> <h3>{{total_p}}</h3>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-success text-white p-3 text-center">
                        <h6>Valor Estoque</h6> <h3>R$ {{valor|round(2)}}</h3>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-danger text-white p-3 text-center">
                        <h6>Serviços</h6> <h3>{{servicos}}</h3>
                    </div>
                </div>
            </div>
            <div class="card p-4 shadow-sm">
                <h5>Resumo de Atividades</h5>
                <canvas id="myChart" style="max-height: 300px;"></canvas>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('myChart');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Fev', 'Mar'],
                    datasets: [{ label: 'Vendas', data: [12, 19, 3], borderWidth: 1 }]
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html, total_p=total_produtos, valor=valor_estoque, servicos=servicos_pendentes)

@app.route('/mapa')
def mapa_interativo():
    # Geolocalização via IP
    try:
        res = requests.get('http://ip-api.com/json/').json()
        lat, lon = res['lat'], res['lon']
        cidade = res['city']
    except:
        lat, lon, cidade = -23.55, -46.63, "Erro Localização"

    # Criando o Mapa Folium
    mapa = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap")
    folium.Marker([lat, lon], popup=f"Oficina em {cidade}", icon=folium.Icon(color='red')).add_to(mapa)
    
    return mapa._repr_html_()

# --- 3. TRAVA DE SEGURANÇA KIVY ---
class LockScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=40, spacing=20, **kwargs)
        self.store = JsonStore('lock.json')
        Window.bind(on_keyboard=lambda w, k, *a: True if k == 27 else False)
        
        self.add_widget(Label(text="PAINEL DE CONTROLE SEGURO", font_size='20sp'))
        self.display = Label(text="[ _ _ _ _ ]", font_size='35sp')
        self.add_widget(self.display)
        
        grid = GridLayout(cols=3, spacing=10, size_hint_y=2)
        for i in range(1, 10):
            btn = Button(text=str(i))
            btn.bind(on_press=self.add_digit); grid.add_widget(btn)
        
        btn_ok = Button(text="ENTRAR", background_color=(0, 1, 0, 1))
        btn_ok.bind(on_press=self.check); grid.add_widget(btn_ok)
        self.add_widget(grid)
        self.input = ""

    def add_digit(self, instance):
        if len(self.input) < 4:
            self.input += instance.text
            self.display.text = "*" * len(self.input)

    def check(self, *args):
        # Para teste, senha padrão '1234' ou a que você definir
        if self.input == "1234":
            webbrowser.open("http://127.0.0.1:5000")
            App.get_running_app().stop()
        else:
            self.input = ""; self.display.text = "ERRO"

class MainApp(App):
    def build(self): return LockScreen()

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    threading.Thread(target=lambda: app.run(port=5000, debug=False, use_reloader=False)).start()
    MainApp().run()