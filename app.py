from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os

app = Flask(__name__)

# Configuración para Railway (usará SQLite temporalmente o podrías conectar tu Postgres de Railway luego)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///products.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# URL de PRODUCCIÓN de n8n (Asegúrate de quitar el "-test")
WEBHOOK_URL = "https://api.sistemaspro.online/webhook-test/nuevo-producto"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    affiliate_link = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'affiliate_link': self.affiliate_link
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
        name = data.get('name')
        affiliate_link = data.get('affiliate_link')

        if not name or not affiliate_link:
            return jsonify({'error': 'Missing data'}), 400

        new_product = Product(name=name, affiliate_link=affiliate_link)
        db.session.add(new_product)
        db.session.commit()

        # ENVÍO A N8N CON LOS CAMPOS CORRECTOS
        try:
            webhook_payload = {
                'nombre': name,  # Coincide con n8n
                'link': affiliate_link # Coincide con n8n
            }
            # Enviamos el POST y no esperamos respuesta para no demorar la web
            requests.post(WEBHOOK_URL, json=webhook_payload, timeout=5)
        except Exception as e:
            print(f"Error sending webhook: {e}")

        return jsonify(new_product.to_dict()), 201

    elif request.method == 'GET':
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)