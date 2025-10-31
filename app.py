from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def webhook():
    user_message = request.form['Body'].lower()
    user_phone = request.form['From']
    
    print(f"Mensaje de {user_phone}: {user_message}")
    
    resp = MessagingResponse()
    
    if 'hola' in user_message:
        resp.message("👋 ¡Hola! Soy tu asistente médico. Opciones: AGENDAR cita, CONFIRMAR cita, CANCELAR cita")
    
    elif 'agendar' in user_message:
        resp.message("📅 Para agendar cita, escribe: AGENDAR [fecha] [hora]. Ejemplo: AGENDAR 25 enero 3pm")
    
    elif 'confirmar' in user_message:
        resp.message("✅ Cita confirmada. ¡Te esperamos!")
    
    elif 'cancelar' in user_message:
        resp.message("❌ Cita cancelada. ¿Quieres agendar nueva cita?")
    
    else:
        resp.message("🤖 Opciones: AGENDAR cita, CONFIRMAR cita, CANCELAR cita")
    
    return str(resp)

@app.route("/")
def home():
    return "Chatbot médico funcionando!"

if __name__ == "__main__":
    print("Iniciando chatbot...")
    app.run(debug=True, port=5000)