from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os 
import re

app = Flask(__name__)

# Base de datos en memoria
citas = {}

@app.route("/webhook", methods=['POST'])
def webhook():
    user_message = request.form['Body'].lower()
    user_phone = request.form['From']
    
    print(f"Mensaje de {user_phone}: {user_message}")
    
    resp = MessagingResponse()
    
    if 'hola' in user_message:
        resp.message("👋 ¡Hola! Soy tu asistente médico. Opciones: AGENDAR cita, CONFIRMAR cita, CANCELAR cita")
    
    elif 'agendar' in user_message:
        # Intentar extraer fecha y hora del mensaje
        if 'agendar' in user_message and len(user_message.split()) > 2:
            # El usuario escribió "AGENDAR 25 febrero 2pm"
            partes = user_message.split()
            if len(partes) >= 4:
                fecha = f"{partes[1]} {partes[2]}"  # "25 febrero"
                hora = partes[3]  # "2pm"
                
                # Guardar la cita
                citas[user_phone] = {
                    'fecha': fecha,
                    'hora': hora,
                    'estado': 'agendada'
                }
                
                resp.message(f"✅ ¡Cita agendada! 📅\nFecha: {fecha}\nHora: {hora}\n\nResponde CONFIRMAR para confirmar tu cita.")
            else:
                resp.message("📅 Por favor escribe: AGENDAR [fía] [mes] [hora]\nEjemplo: AGENDAR 25 febrero 2pm")
        else:
            resp.message("📅 Para agendar cita, escribe: AGENDAR [fecha] [hora]\nEjemplo: AGENDAR 25 enero 3pm")
    
    elif 'confirmar' in user_message:
        if user_phone in citas:
            cita = citas[user_phone]
            resp.message(f"✅ ¡CITA CONFIRMADA! 🎉\n📅 Fecha: {cita['fecha']}\n⏰ Hora: {cita['hora']}\n\n¡Te esperamos en tu consulta! 🏥")
        else:
            resp.message("❌ No tienes citas pendientes para confirmar.")
    
    elif 'cancelar' in user_message:
        if user_phone in citas:
            del citas[user_phone]
            resp.message("❌ Cita cancelada. ¿Quieres agendar una nueva cita?")
        else:
            resp.message("❌ No tienes citas para cancelar.")
    
    else:
        resp.message("🤖 Opciones: AGENDAR cita, CONFIRMAR cita, CANCELAR cita")
    
    return str(resp)

@app.route("/")
def home():
    return "Chatbot médico funcionando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)