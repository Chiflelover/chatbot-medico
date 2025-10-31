from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os 
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

# ==================== CONFIGURACIÓN FIREBASE ====================
db = None
try:
    firebase_config_json = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_config_json:
        firebase_config = json.loads(firebase_config_json)
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase conectado exitosamente")
except Exception as e:
    print(f"❌ Error Firebase: {e}")

app = Flask(__name__)

# ==================== ESTADOS DE USUARIO ====================
estados_usuarios = {}

# ==================== HORARIOS DISPONIBLES ====================
HORARIOS_DISPONIBLES = [
    "08:00", "09:00", "10:00", "11:00", 
    "14:00", "15:00", "16:00", "17:00"
]

# ==================== FUNCIONES FIREBASE ====================
def guardar_cita_firebase(patient_phone, patient_name, fecha, hora, status="confirmada"):
    """Guarda una cita en Firebase"""
    if db is None:
        print("⚠️ Modo sin Firebase - cita no guardada en BD")
        return True
        
    try:
        cita_data = {
            'patient_phone': patient_phone,
            'patient_name': patient_name,
            'appointment_date': fecha,
            'appointment_time': hora,
            'status': status,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('appointments').add(cita_data)
        print(f"✅ Cita guardada para {patient_name}: {fecha} {hora}")
        return True
    except Exception as e:
        print(f"❌ Error guardando en Firebase: {e}")
        return False

def obtener_citas_paciente(patient_phone):
    """Obtiene las citas de un paciente"""
    if db is None:
        return []
        
    try:
        citas_ref = db.collection('appointments')
        query = citas_ref.where('patient_phone', '==', patient_phone)
        citas = query.stream()
        
        citas_lista = []
        for cita in citas:
            cita_data = cita.to_dict()
            cita_data['id'] = cita.id
            citas_lista.append(cita_data)
            
        return citas_lista
    except Exception as e:
        print(f"❌ Error obteniendo citas: {e}")
        return []

def verificar_horario_disponible(fecha, hora):
    """Verifica si un horario está disponible"""
    if db is None:
        return True
        
    try:
        citas_ref = db.collection('appointments')
        query = citas_ref.where('appointment_date', '==', fecha).where('appointment_time', '==', hora)
        citas = query.stream()
        
        return len(list(citas)) == 0
    except Exception as e:
        print(f"❌ Error verificando horario: {e}")
        return True

def normalizar_hora(hora_str):
    """Convierte formatos de hora como '8:00' a '08:00'"""
    try:
        hora_str = hora_str.strip()
        if hora_str in HORARIOS_DISPONIBLES:
            return hora_str
            
        if ':' in hora_str:
            partes = hora_str.split(':')
            horas = partes[0].zfill(2)
            minutos = partes[1] if len(partes) > 1 else "00"
            return f"{horas}:{minutos}"
        else:
            return f"{hora_str.zfill(2)}:00"
    except:
        return hora_str

# ==================== RUTAS DEL CHATBOT ====================
@app.route("/webhook", methods=['POST'])
def webhook():
    user_message = request.form['Body'].lower()
    user_phone = request.form['From']
    
    print(f"📱 Mensaje de {user_phone}: {user_message}")
    
    resp = MessagingResponse()
    
    # Verificar si está en medio de una conversación para nombre
    if user_phone in estados_usuarios and estados_usuarios[user_phone]['accion'] == 'esperando_nombre':
        nombre_paciente = user_message.strip()
        datos_temporales = estados_usuarios[user_phone]
        
        if guardar_cita_firebase(user_phone, nombre_paciente, datos_temporales['fecha'], datos_temporales['hora']):
            del estados_usuarios[user_phone]
            
            resp.message(f"""✅ *¡CITA AGENDADA EXITOSAMENTE!*

👤 Paciente: {nombre_paciente}
📅 Fecha: {datos_temporales['fecha']}
🕐 Hora: {datos_temporales['hora']}
🏥 Estado: CONFIRMADA

Recibirás un recordatorio antes de tu cita. ¡Te esperamos!""")
        else:
            resp.message("❌ Error al guardar la cita. Intenta nuevamente.")
        
        return str(resp)
    
    # Comandos normales
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
                hora_input = partes[3]
                hora_normalizada = normalizar_hora(hora_input)
                
                if hora_normalizada in HORARIOS_DISPONIBLES:
                    if verificar_horario_disponible(fecha, hora_normalizada):
                        estados_usuarios[user_phone] = {
                            'accion': 'esperando_nombre',
                            'fecha': fecha,
                            'hora': hora_normalizada
                        }
                        resp.message("📝 Por favor, escribe tu *NOMBRE COMPLETO* para confirmar la cita:")
                    else:
                        resp.message(f"❌ El horario {hora_normalizada} del {fecha} ya está ocupado. Escribe HORARIOS para ver disponibilidad.")
                else:
                    mensaje_error = f"❌ Horario '{hora_input}' no válido.\n\n🕐 *Horarios disponibles:*\n"
                    for i, hora in enumerate(HORARIOS_DISPONIBLES, 1):
                        mensaje_error += f"{i}. {hora}\n"
                    resp.message(mensaje_error)
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
                nombre = cita.get('patient_name', 'Paciente')
                mensaje += f"{i}. 👤 {nombre} - 📅 {cita.get('appointment_date', 'N/A')} - 🕐 {cita.get('appointment_time', 'N/A')}\n"
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

@app.route("/")
def home():
    estado_firebase = "conectado" if db else "no conectado"
    return f"Sistema de citas médicas funcionando! Firebase: {estado_firebase}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)