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
    firebase_config_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    
    # DEBUG: Ver qué está pasando
    print(f"🔍 Longitud de FIREBASE_SERVICE_ACCOUNT_JSON: {len(firebase_config_json) if firebase_config_json else 'VACÍA'}")
    
    if firebase_config_json:
        # Verificar que sea un JSON válido
        firebase_config = json.loads(firebase_config_json)
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase conectado exitosamente")
    else:
        print("⚠️  Firebase no configurado - FIREBASE_SERVICE_ACCOUNT_JSON no encontrada")
        
except json.JSONDecodeError as e:
    print(f"❌ Error en formato JSON: {e}")
except Exception as e:
    print(f"❌ Error Firebase: {e}")

app = Flask(__name__)

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
        # Intentar con ambos formatos de campos para mayor compatibilidad
        cita_data = {
            'patient_phone': patient_phone,      # Formato nuevo
            'partent_phone': patient_phone,      # Formato viejo (si existe)
            'patient_name': patient_name,        # Formato nuevo  
            'partent_name': patient_name,        # Formato viejo (si existe)
            'appointment_date': fecha,           # Formato que existe en tu BD
            'appointment_time': hora,            # Formato que existe en tu BD
            'fecha': fecha,                      # Formato nuevo por si acaso
            'hora': hora,                        # Formato nuevo por si acaso
            'status': status,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('appointments').document()
        doc_ref.set(cita_data)
        print(f"✅ Cita guardada en Firebase: {fecha} {hora} para {patient_phone}")
        return True
    except Exception as e:
        print(f"❌ Error guardando en Firebase: {e}")
        return False

def obtener_citas_paciente(patient_phone):
    """Obtiene las citas de un paciente"""
    if db is None:
        print("⚠️ Modo sin Firebase - retornando lista vacía")
        return []
        
    try:
        citas_ref = db.collection('appointments')
        
        # Intentar buscar con ambos nombres de campo
        citas_lista = []
        try:
            query = citas_ref.where('patient_phone', '==', patient_phone)
            citas = query.stream()
            citas_lista = list(citas)
        except:
            # Si falla, intentar con el nombre alternativo
            query = citas_ref.where('partent_phone', '==', patient_phone)
            citas = query.stream()
            citas_lista = list(citas)
        
        citas_data = []
        for cita in citas_lista:
            cita_data = cita.to_dict()
            cita_data['id'] = cita.id
            citas_data.append(cita_data)
            
        print(f"✅ Obtenidas {len(citas_data)} citas para {patient_phone}")
        return citas_data
    except Exception as e:
        print(f"❌ Error obteniendo citas: {e}")
        return []

def verificar_horario_disponible(fecha, hora):
    """Verifica si un horario está disponible"""
    if db is None:
        print("⚠️ Modo sin Firebase - horario siempre disponible")
        return True
        
    try:
        citas_ref = db.collection('appointments')
        
        # Intentar con ambos formatos de fecha/hora
        try:
            query = citas_ref.where('appointment_date', '==', fecha).where('appointment_time', '==', hora)
            citas = query.stream()
        except:
            query = citas_ref.where('fecha', '==', fecha).where('hora', '==', hora)
            citas = query.stream()
        
        disponible = len(list(citas)) == 0
        print(f"🔍 Horario {fecha} {hora} - Disponible: {disponible}")
        return disponible
    except Exception as e:
        print(f"❌ Error verificando horario: {e}")
        return True

# ==================== RUTAS DEL CHATBOT ====================
@app.route("/webhook", methods=['POST'])
def webhook():
    user_message = request.form['Body'].lower()
    user_phone = request.form['From']
    
    print(f"📱 Mensaje de {user_phone}: {user_message}")
    
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
                    if verificar_horario_disponible(fecha, hora):
                        # Guardar la cita en Firebase
                        nombre_paciente = "Paciente"  # Podemos pedir el nombre después
                        if guardar_cita_firebase(user_phone, nombre_paciente, fecha, hora):
                            resp.message(f"""✅ *¡CITA AGENDADA EXITOSAMENTE!*

📅 Fecha: {fecha}
🕐 Hora: {hora}
🏥 Estado: CONFIRMADA

Recibirás un recordatorio antes de tu cita. ¡Te esperamos!""")
                        else:
                            resp.message("❌ Error al guardar la cita en el sistema. Intenta nuevamente.")
                    else:
                        resp.message(f"❌ El horario {hora} del {fecha} ya está ocupado. Escribe HORARIOS para ver disponibilidad.")
                else:
                    resp.message(f"❌ Horario no válido. Escribe HORARIOS para ver los horarios disponibles.")
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

@app.route("/")
def home():
    estado_firebase = "conectado" if db else "no conectado"
    return f"Sistema de citas médicas funcionando! Firebase: {estado_firebase}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)