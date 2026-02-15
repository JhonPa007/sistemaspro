from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os

app = Flask(__name__)

# Configuración para Railway (usará SQLite temporalmente o podrías conectar tu Postgres de Railway luego)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# URL de PRODUCCIÓN de n8n (Asegúrate de quitar el "-test")
WEBHOOK_URL = "https://api.sistemaspro.online/webhook/nuevo-producto"

class Product(db.Model):
    __tablename__ = 'afiliados_master'
    id = db.Column(db.Integer, primary_key=True)
    nombre_producto = db.Column(db.String(100), nullable=False)
    link_afiliado = db.Column(db.String(255), nullable=False)
    analisis_ia = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre_producto': self.nombre_producto,
            'link_afiliado': self.link_afiliado,
            'analisis_ia': self.analisis_ia
        }

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products', methods=['GET', 'POST'])
def handle_products():
    if request.method == 'POST':
        data = request.json
        nombre_producto = data.get('nombre_producto')
        link_afiliado = data.get('link_afiliado')

        if not nombre_producto or not link_afiliado:
            return jsonify({'error': 'Missing data'}), 400

        try:
            new_product = Product(nombre_producto=nombre_producto, link_afiliado=link_afiliado)
            db.session.add(new_product)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

        # ENVÍO A N8N CON LOS CAMPOS CORRECTOS
        try:
            webhook_payload = {
                'id': new_product.id, # ID único de DB para hacer Update en n8n
                'nombre': nombre_producto,  # Coincide con n8n
                'link': link_afiliado # Coincide con n8n
            }
            # Enviamos el POST y no esperamos respuesta para no demorar la web
            requests.post(WEBHOOK_URL, json=webhook_payload, timeout=5)
        except Exception as e:
            print(f"Error sending webhook: {e}")

        return jsonify(new_product.to_dict()), 201

    elif request.method == 'GET':
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products])

@app.route('/producto/<int:product_id>')
def view_analysis(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('analysis.html', product=product)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)