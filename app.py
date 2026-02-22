from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from flask_mail import Mail, Message

app = Flask(__name__)

# Configuración de Flask-Mail (Zoho)
app.config['MAIL_SERVER'] = 'smtp.zoho.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'jhon.casas@sistemaspro.online'
app.config['MAIL_PASSWORD'] = 'C4S4sJh0n*' # En producción, usar os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'jhon.casas@sistemaspro.online'

mail = Mail(app)

# Configuración para Railway (usará SQLite temporalmente o podrías conectar tu Postgres de Railway luego)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# URL de PRODUCCIÓN de n8n (Asegúrate de quitar el "-test")
WEBHOOK_URL = "https://api.sistemaspro.online/webhook/nuevo-producto"
# Webhook para Auditoría Gratuita (Reemplazar con URL real)
N8N_AUDIT_WEBHOOK = "https://api.sistemaspro.online/webhook/nuevo-prospecto"

class Product(db.Model):
    __tablename__ = 'afiliados_master'
    id = db.Column(db.Integer, primary_key=True)
    nombre_producto = db.Column(db.String(100), nullable=False)
    link_afiliado = db.Column(db.String(255), nullable=False)
    analisis_ia = db.Column(db.Text, nullable=True)
    outreach_emails = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre_producto': self.nombre_producto,
            'link_afiliado': self.link_afiliado,
            'analisis_ia': self.analisis_ia,
            'outreach_emails': self.outreach_emails
        }

with app.app_context():
    db.create_all()

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/admin-panel-privado')
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

@app.route('/enviar-consulta', methods=['POST'])
def enviar_consulta():
    data = request.json
    nombre = data.get('nombre')
    email = data.get('email')
    empresa = data.get('empresa')
    url_sitio = data.get('url_sitio', 'No especificado')
    solucion = data.get('solucion')
    mensaje = data.get('mensaje')

    if not nombre or not email:
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    # 1. Correo al Administrador (Lead)
    try:
        msg_admin = Message(
            subject=f'Nuevo Lead: {empresa} - {solucion}',
            recipients=['jhon.casas@sistemaspro.online'],
            body=f"""
Nuevo contacto desde la web:

Nombre: {nombre}
Empresa: {empresa}
Sitio Web: {url_sitio}
Email: {email}
Solución de Interés: {solucion}

Mensaje:
{mensaje}
            """
        )
        mail.send(msg_admin)

        # 2. Auto-respuesta al Cliente
        msg_cliente = Message(
            subject='Recibimos tu consulta - SistemasPro AI',
            recipients=[email],
            body=f"""Hola {nombre},

Gracias por contactar a SistemasPro AI. Hemos recibido tu consulta sobre {solucion} para {empresa}.

Mientras nuestro equipo analiza tu caso, queremos recordarte por qué somos la elección segura para tu implementación de IA:

1. SEGURIDAD EMPRESARIAL: Operamos bajo estándares SOC-2 Type 2 y GDPR. Tus datos nunca se usan para entrenar modelos públicos.
2. CERO ALUCINACIONES: Nuestra tecnología RAG cita fuentes verificables en cada respuesta, eliminando riesgos legales.
3. ROI INMEDIATO: Nuestros clientes reportan un ahorro promedio del 50% en costos operativos desde el primer mes.

Un consultor experto te contactará en breve para agendar una demostración personalizada.

Atentamente,
El equipo de SistemasPro AI
SistemasPro.online
            """
        )
        mail.send(msg_cliente)

        return jsonify({'message': 'Correo enviado correctamente'}), 200

        return jsonify({'message': 'Correo enviado correctamente'}), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error enviando correo: {e}")
        print(error_details)
        # Return specific error to frontend for debugging
        return jsonify({'error': f'Error al enviar el mensaje: {str(e)}'}), 500
        return jsonify({'error': 'Error al enviar el mensaje'}), 500

@app.route('/solicitar-auditoria', methods=['POST'])
def solicitar_auditoria():
    data = request.json
    nombre = data.get('nombre')
    email = data.get('email')
    empresa = data.get('empresa')
    url_web = data.get('url_web')

    if not nombre or not email or not url_web:
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    # Enviar datos a n8n
    try:
        payload = {
            'nombre': nombre,
            'email': email,
            'empresa': empresa,
            'url_web': url_web,
            'tipo': 'auditoria_gratuita'
        }
        
        print(f"Enviando payload a n8n ({N8N_AUDIT_WEBHOOK}): {payload}")
        
        response = requests.post(N8N_AUDIT_WEBHOOK, json=payload, timeout=10)
        
        print(f"Respuesta de n8n: {response.status_code} - {response.text}")
        
        if response.status_code != 200:
            print(f"ADVERTENCIA: n8n respondió con error {response.status_code}")

        return jsonify({'message': 'Estamos analizando tu sitio web, recibirás una propuesta personalizada en unos minutos'}), 200

    except Exception as e:
        import traceback
        print(f"ERROR CRÍTICO contactando n8n: {e}")
        print(traceback.format_exc())
        # Return success to UI but log error
        return jsonify({'message': 'Estamos analizando tu sitio web, recibirás una propuesta personalizada en unos minutos'}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)