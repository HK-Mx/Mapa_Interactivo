# app.py
import os
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# --- Configuración de la Base de Datos MongoDB ---
MONGO_URI = os.getenv("DATABASE_URL")
if not MONGO_URI:
    logging.error("DATABASE_URL environment variable not set.")
    # En un entorno de producción, esto debería ser un error fatal o una configuración predeterminada segura.
    # Para desarrollo local, puedes establecer una URL de fallback o salir.
    raise ValueError("DATABASE_URL environment variable not set. Please set it in your .env file or environment.")

try:
    client = MongoClient(MONGO_URI)
    # Asume que el nombre de la base de datos es 'Cluster0' de la URL proporcionada
    db = client.Cluster0
    events_collection = db.event # Asume que la colección se llama 'events'
    logging.info("Conexión a MongoDB establecida con éxito.")
except Exception as e:
    logging.error(f"Error al conectar con MongoDB: {e}")
    raise

# --- Configuración de la API de Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY environment variable not set.")
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it in your .env file or environment.")

genai.configure(api_key=GEMINI_API_KEY)

# --- Herramienta de Búsqueda para Gemini (Simulada) ---
# Esta función simula una búsqueda en internet.
# En una aplicación real, esto se integraría con una API de búsqueda real
# (ej., Google Custom Search, SerpAPI, etc.).
def search_internet(query: str) -> str:
    """
    Realiza una búsqueda simulada en internet para la consulta dada.
    """
    logging.info(f"Simulando búsqueda en internet para: {query}")
    # Resultados de búsqueda simulados para demostración
    if "tech event" in query.lower() or "startup event" in query.lower() or "evento de tecnología" in query.lower():
        return f"Resultados de búsqueda para '{query}': Eventos de tecnología y startups suelen cubrir temas como IA, blockchain, SaaS, financiación de startups y networking. Muchos eventos presentan pitches de startups, sesiones de mentoría y oportunidades de inversión. La innovación es clave."
    elif "blockchain" in query.lower():
        return f"Resultados de búsqueda para '{query}': Blockchain es una tecnología de registro distribuido que sustenta criptomonedas como Bitcoin y Ethereum. Se utiliza para contratos inteligentes, NFTs, finanzas descentralizadas (DeFi) y trazabilidad en la cadena de suministro. Es una tecnología disruptiva."
    elif "ia" in query.lower() or "inteligencia artificial" in query.lower():
        return f"Resultados de búsqueda para '{query}': La Inteligencia Artificial (IA) es un campo de la informática que se enfoca en la creación de máquinas inteligentes que funcionan y reaccionan como humanos. Incluye aprendizaje automático (Machine Learning), procesamiento de lenguaje natural (NLP), visión por computadora y robótica. La IA está transformando industrias."
    elif "fintech" in query.lower() or "finanzas" in query.lower():
        return f"Resultados de búsqueda para '{query}': Fintech se refiere a la tecnología financiera que busca mejorar y automatizar la prestación y el uso de servicios financieros. Incluye pagos móviles, préstamos online, gestión de inversiones automatizada y criptomonedas. Es un sector de rápido crecimiento."
    elif "saas" in query.lower() or "software como servicio" in query.lower():
        return f"Resultados de búsqueda para '{query}': Software as a Service (SaaS) es un modelo de entrega de software donde el software es licenciado por suscripción y se aloja centralmente. Es una forma común de ofrecer aplicaciones empresariales y de consumo. Ofrece escalabilidad y accesibilidad."
    else:
        return f"Resultados de búsqueda para '{query}': Información general sobre {query}. Podría incluir noticias, definiciones, tendencias recientes o aplicaciones."

# Define la herramienta para el modelo Gemini
search_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='search_internet',
            description='Performs a simulated internet search for the given query related to tech, startups, or specific technologies.',
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'query': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=['query']
            )
        )
    ]
)

# Inicializa el modelo Gemini con la herramienta definida
# Se recomienda usar un modelo como 'gemini-1.5-flash' o 'gemini-1.0-pro' para un buen rendimiento.
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[search_tool]
)

# --- Rutas de Flask ---

@app.route('/')
def index():
    """Sirve la página principal de la aplicación."""
    return render_template('index.html')

@app.route('/api/events', methods=['GET'])
def get_events():
    """
    Obtiene eventos de la base de datos MongoDB, aplicando filtros de fecha y ubicación.
    Los parámetros de la URL son:
    - startDate (ISO format): Fecha de inicio mínima.
    - endDate (ISO format): Fecha de fin máxima.
    - location (string): Ubicación a buscar (búsqueda insensible a mayúsculas/minúsculas).
    """
    start_date_str = request.args.get('startDate')
    end_date_str = request.args.get('endDate')
    location_filter = request.args.get('location')

    query = {}
    if start_date_str:
        try:
            # Reemplazar 'Z' por '+00:00' para compatibilidad con fromisoformat
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            query['initialDate'] = {'$gte': start_date}
        except ValueError:
            logging.warning(f"Formato de fecha de inicio inválido: {start_date_str}")
            return jsonify({"error": "Formato de fecha de inicio inválido. Use ISO 8601 (ej. 2025-05-21T00:00:00Z)"}), 400
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            query['finalDate'] = {'$lte': end_date}
        except ValueError:
            logging.warning(f"Formato de fecha de fin inválido: {end_date_str}")
            return jsonify({"error": "Formato de fecha de fin inválido. Use ISO 8601 (ej. 2025-05-23T00:00:00Z)"}), 400
    if location_filter:
        # Búsqueda de ubicación insensible a mayúsculas/minúsculas
        query['location'] = {'$regex': location_filter, '$options': 'i'}

    try:
        events_cursor = events_collection.find(query)
        events_list = []
        for event in events_cursor:
            # Convertir ObjectId a string para serialización JSON
            event['_id'] = str(event['_id'])
            # Convertir objetos datetime a strings ISO para serialización JSON
            if 'initialDate' in event and isinstance(event['initialDate'], datetime):
                event['initialDate'] = event['initialDate'].isoformat() + 'Z'
            if 'finalDate' in event and isinstance(event['finalDate'], datetime):
                event['finalDate'] = event['finalDate'].isoformat() + 'Z'
            events_list.append(event)
        logging.info(f"Eventos encontrados: {len(events_list)}")
        return jsonify(events_list)
    except Exception as e:
        logging.error(f"Error al obtener eventos de MongoDB: {e}")
        return jsonify({"error": "Fallo al obtener eventos", "details": str(e)}), 500

@app.route('/api/gemini_analysis', methods=['POST'])
def gemini_analysis():
    """
    Endpoint para obtener un análisis de Gemini sobre la relevancia de un evento.
    Recibe:
    - eventName (string): Nombre del evento.
    - startupDescription (string): Descripción de la startup asociada al evento.
    - eventTheme (string, opcional): Temática general del evento.
    """
    data = request.json
    event_name = data.get('eventName')
    startup_description = data.get('startupDescription')
    # Proporciona una temática por defecto si no se especifica
    event_theme = data.get('eventTheme', 'tecnología, startups e innovación')

    if not event_name or not startup_description:
        logging.warning("Solicitud de análisis de Gemini incompleta: falta eventName o startupDescription.")
        return jsonify({"error": "Faltan 'eventName' o 'startupDescription' en la solicitud."}), 400

    prompt = f"""
    Eres un asistente experto en el ecosistema de eventos de tecnología, startups e innovación. Tu objetivo es proporcionar una evaluación concisa sobre si un evento específico, en relación con una startup, sería de interés para un usuario que busca oportunidades en el ámbito tecnológico, de inversión, o de desarrollo de nuevas empresas.

    Aquí tienes la información clave:
    - Nombre del Evento: "{event_name}"
    - Temática General del Evento (si aplica): "{event_theme}"
    - Descripción de la Startup asociada: "{startup_description}"

    Tu proceso de análisis debe ser el siguiente:
    1.  **Investigación Contextual**: Utiliza la herramienta `search_internet` para buscar información relevante sobre la temática del evento y los conceptos clave presentes en la descripción de la startup. Esto te ayudará a entender el dominio y la relevancia.
    2.  **Evaluación de Interés**: Basado en la información recopilada y la descripción de la startup, determina si el evento y la participación de esta startup se alinean con los intereses típicos de un entusiasta de startups, un inversor potencial, o alguien que busca innovación en tecnología. Considera si el evento ofrece networking, conocimiento de tendencias, oportunidades de financiación o visibilidad para nuevas empresas.
    3.  **Generación de Respuesta**: Crea una respuesta clara y concisa de aproximadamente 500 caracteres.

    **Si el evento es de interés**:
    Explica brevemente por qué es relevante, destacando qué oportunidades o beneficios podría ofrecer para alguien interesado en startups y tecnología. Menciona cómo la startup se relaciona con la temática del evento y por qué esto es valioso.

    **Si el evento NO es de interés (o es menos relevante)**:
    Explica concisamente por qué no se alinea bien con los intereses de startups/tecnología, y sugiere qué tipo de eventos o temáticas alternativas (con ejemplos) podrían ser más adecuadas para ese perfil de usuario.

    **Formato de la Respuesta**:
    - Si es de interés: "¡Este evento es muy prometedor para tus intereses! [Explicación concisa de por qué, mencionando la startup y la temática. Máx. ~500 caracteres]"
    - Si NO es de interés: "Este evento parece menos alineado con tus objetivos en startups. [Explicación concisa y sugerencias de temáticas alternativas. Máx. ~500 caracteres]"
    """

    try:
        # Iniciar un chat con el modelo
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)

        # Manejar llamadas a herramientas (si el modelo decide usar search_internet)
        if response.candidates and response.candidates[0].function_calls:
            for call in response.candidates[0].function_calls:
                if call.name == 'search_internet':
                    # Ejecutar la función simulada de búsqueda
                    tool_response_content = search_internet(call.args['query'])
                    # Enviar la respuesta de la herramienta de vuelta al modelo
                    response = chat.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name='search_internet',
                                response={
                                    'result': tool_response_content
                                }
                            )
                        )
                    )
        # Asegurarse de que hay una respuesta de texto después de posibles llamadas a herramientas
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            gemini_output = response.candidates[0].content.parts[0].text
            # Truncar la salida a aproximadamente 500 caracteres
            if len(gemini_output) > 500:
                gemini_output = gemini_output[:497] + "..." # Añade puntos suspensivos si se trunca
            logging.info(f"Análisis de Gemini generado para '{event_name}': {gemini_output}")
            return jsonify({"analysis": gemini_output})
        else:
            logging.warning(f"Gemini no devolvió una respuesta de texto válida para '{event_name}'.")
            return jsonify({"error": "Gemini no pudo generar un análisis válido."}), 500

    except Exception as e:
        logging.error(f"Error al llamar a la API de Gemini para '{event_name}': {e}")
        return jsonify({"error": "Fallo al obtener el análisis de Gemini", "details": str(e)}), 500

# --- Lógica de Inserción de Datos de Prueba (Solo para desarrollo/primera ejecución) ---
if __name__ == '__main__':
    # Esta sección inserta datos de prueba si la colección 'events' está vacía.
    # Es útil para probar la aplicación sin tener que añadir datos manualmente.
    # En un entorno de producción, los datos se gestionarían de otra manera.
    try:
        if events_collection.count_documents({}) == 0:
            logging.info("No se encontraron eventos en la base de datos. Insertando datos de prueba...")
            dummy_events = [
                {
                    "id": "687bbf5995aa2580f6dec88e",
                    "name": "Latitude 59",
                    "initialDate": datetime(2025, 5, 21, 0, 0, 0),
                    "finalDate": datetime(2025, 5, 23, 0, 0, 0),
                    "location": "Tallinn",
                    "website": "https://latitude59.ee/",
                    "location_point": {
                        "type": "Point",
                        "coordinates": [24.7453688, 59.4372155] # [longitude, latitude]
                    },
                    "description": "Startup InnovaTech es una empresa de IA que desarrolla soluciones de procesamiento de lenguaje natural para el sector financiero, enfocándose en la automatización de análisis de mercado y detección de fraudes."
                },
                {
                    "id": "a1b2c3d4e5f6g7h8i9j0k1l2",
                    "name": "Slush",
                    "initialDate": datetime(2025, 11, 30, 0, 0, 0),
                    "finalDate": datetime(2025, 12, 1, 0, 0, 0),
                    "location": "Helsinki",
                    "website": "https://www.slush.org/",
                    "location_point": {
                        "type": "Point",
                        "coordinates": [24.9384, 60.1699]
                    },
                    "description": "CryptoLedger Solutions crea soluciones de blockchain para la gestión de la cadena de suministro, enfocándose en la trazabilidad y la transparencia de productos agrícolas desde la granja hasta el consumidor."
                },
                {
                    "id": "m3n4o5p6q7r8s9t0u1v2w3x4",
                    "name": "Web Summit",
                    "initialDate": datetime(2025, 11, 11, 0, 0, 0),
                    "finalDate": datetime(2025, 11, 14, 0, 0, 0),
                    "location": "Lisbon",
                    "website": "https://websummit.com/",
                    "location_point": {
                        "type": "Point",
                        "coordinates": [-9.1393, 38.7223]
                    },
                    "description": "CloudConnect Global es una plataforma SaaS que optimiza la colaboración remota para equipos distribuidos, integrando herramientas de comunicación, gestión de proyectos y compartición de documentos para mejorar la productividad empresarial."
                },
                {
                    "id": "y5z6a7b8c9d0e1f2g3h4i5j6",
                    "name": "Mobile World Congress",
                    "initialDate": datetime(2026, 2, 24, 0, 0, 0),
                    "finalDate": datetime(2026, 2, 27, 0, 0, 0),
                    "location": "Barcelona",
                    "website": "https://www.mwcbarcelona.com/",
                    "location_point": {
                        "type": "Point",
                        "coordinates": [2.154007, 41.390205]
                    },
                    "description": "NextGen IoT desarrolla hardware y software para la próxima generación de redes 5G y soluciones IoT, con un enfoque en ciudades inteligentes y optimización del consumo energético en entornos urbanos."
                },
                {
                    "id": "z7x8c9v0b1n2m3l4k5j6h7g8",
                    "name": "TechCrunch Disrupt",
                    "initialDate": datetime(2025, 9, 15, 0, 0, 0),
                    "finalDate": datetime(2025, 9, 17, 0, 0, 0),
                    "location": "San Francisco",
                    "website": "https://techcrunch.com/events/disrupt/",
                    "location_point": {
                        "type": "Point",
                        "coordinates": [-122.4194, 37.7749]
                    },
                    "description": "BioMed Innovations es una startup de biotecnología que utiliza IA para acelerar el descubrimiento de fármacos y personalizar tratamientos médicos, con un enfoque en enfermedades raras."
                }
            ]
            try:
                events_collection.insert_many(dummy_events)
                logging.info(f"Se insertaron {len(dummy_events)} datos de prueba con éxito.")
            except Exception as e:
                logging.error(f"Error al insertar datos de prueba: {e}")
        else:
            logging.info("La base de datos ya contiene eventos. No se insertaron datos de prueba.")
    except Exception as e:
        logging.error(f"Error al verificar la colección de eventos: {e}")


    # Iniciar la aplicación Flask
    # host='0.0.0.0' permite que la aplicación sea accesible desde cualquier IP (necesario en entornos de contenedor como Render)
    # port se obtiene de la variable de entorno PORT (Render la establece) o por defecto a 5000
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))

