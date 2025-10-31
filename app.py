from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os 
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# Configuración de Firebase (usa tu código actual)

app = Flask(__name__)

# Horarios disponibles predefinidos
HORARIOS_DISPONIBLES = [
    "08:00", "09:00", "10:00", "11:00", 
    "14:00", "15:00", "16:00", "17:00"
]

@app.route("/webhook", methods=['POST'])
def webhook():
    user_message = request.form['Body'].lower()
    user_phone = request.form['From']
    
    print(f"Mensaje de {user_phone}: {user_message}")
    
    resp = MessagingResponse()
    
    if 'hola' in user_message:
        mensaje = """👋 ¡Hola! Soy tu asistente médico. 

📋 *Opciones disponibles:*
• AGENDAR - Programar una cita médica
• HORARIOS - Ver horarios disponibles  
• MIS CITAS - Ver mis citas confirmadas
• CANCELAR - Cancelar una cita

¿En qué puedo ayudarte?"""
        resp.message(mensaje)
    
    elif 'horarios' in user_message:
        mensaje = "🕐 *Horarios disponibles:*\n\n"
        for i, hora in enumerate(HORARIOS_DISPONIBLES, 1):
            mensaje += f"{i}. {hora}\n"
        mensaje += "\nPara agendar, escribe: AGENDAR [fecha] [hora]\nEjemplo: AGENDAR 15 noviembre 10:00"
        resp.message(mensaje)
    
    elif 'agendar' in user_message:
        if len(user_message.split()) >= 3:
            partes = user_message.split()
            fecha = f"{partes[1]} {partes[2]}"  # "15 noviembre"
            
            if len(partes) >= 4:
                hora = partes[3]  # "10:00"
                
                # Verificar si el horario está disponible
                if hora in HORARIOS_DISPONIBLES:
                    # Verificar si el horario ya está ocupado
                    if verificar_horario_disponible(fecha, hora):
                        # Guardar la cita
                        if guardar_cita_firebase(user_phone, "Paciente", fecha, hora):
                            resp.message(f"""✅ *¡CITA AGENDADA EXITOSAMENTE!*

📅 Fecha: {fecha}
🕐 Hora: {hora}
🏥 Estado: CONFIRMADA

Recibirás un recordatorio antes de tu cita. ¡Te esperamos!""")
                        else:
                            resp.message("❌ Error al guardar la cita. Intenta nuevamente.")
                    else:
                        resp.message(f"❌ El horario {hora} del {fecha} ya está ocupado. Elige otro horario.")
                else:
                    resp.message(f"❌ Horario no válido. Horarios disponibles: {', '.join(HORARIOS_DISPONIBLES)}")
            else:
                resp.message("❌ Formato incorrecto. Usa: AGENDAR [día] [mes] [hora]\nEjemplo: AGENDAR 15 noviembre 10:00")
        else:
            resp.message("""📅 Para agendar una cita:

Escribe: AGENDAR [día] [mes] [hora]

📝 *Ejemplos:*
• AGENDAR 15 noviembre 10:00
• AGENDAR 20 noviembre 14:00

Escribe HORARIOS para ver disponibilidad.""")
    
    elif 'mis citas' in user_message or 'citas' in user_message:
        citas = obtener_citas_paciente(user_phone)
        if citas:
            mensaje = "📋 *Tus citas confirmadas:*\n\n"
            for i, cita in enumerate(citas, 1):
                mensaje += f"{i}. 📅 {cita.get('fecha', 'N/A')} - 🕐 {cita.get('hora', 'N/A')}\n"
            resp.message(mensaje)
        else:
            resp.message("📭 No tienes citas agendadas.\n\nEscribe AGENDAR para programar una cita.")
    
    elif 'cancelar' in user_message:
        resp.message("❌ Para cancelar una cita, por favor contacta directamente a la clínica al 📞 555-1234")
    
    else:
        resp.message("""🤖 No entendí tu mensaje. 

📋 *Opciones disponibles:*
• AGENDAR - Programar cita médica
• HORARIOS - Ver horarios disponibles
• MIS CITAS - Ver citas confirmadas
• CANCELAR - Cancelar cita""")
    
    return str(resp)

def verificar_horario_disponible(fecha, hora):
    """Verifica si un horario está disponible"""
    try:
        if db is None:
            return True
            
        citas_ref = db.collection('appointments')
        query = citas_ref.where('fecha', '==', fecha).where('hora', '==', hora)
        citas = query.stream()
        
        return len(list(citas)) == 0
    except Exception as e:
        print(f"Error verificando horario: {e}")
        return True

def guardar_cita_firebase(patient_phone, patient_name, fecha, hora, status="confirmada"):
    """Guarda una cita en Firebase"""
    if db is None:
        return True
        
    try:
        cita_data = {
            'patient_phone': patient_phone,
            'patient_name': patient_name,
            'fecha': fecha,
            'hora': hora,
            'status': status,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('appointments').add(cita_data)
        return True
    except Exception as e:
        print(f"Error guardando cita: {e}")
        return False

def obtener_citas_paciente(patient_phone):
    """Obtiene las citas de un paciente"""
    if db is None:
        return []
        
    try:
        citas_ref = db.collection('appointments')
        query = citas_ref.where('patient_phone', '==', patient_phone).where('status', '==', 'confirmada')
        citas = query.stream()
        
        return [cita.to_dict() for cita in citas]
    except Exception as e:
        print(f"Error obteniendo citas: {e}")
        return []

@app.route("/")
def home():
    return "Sistema de citas médicas funcionando!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)