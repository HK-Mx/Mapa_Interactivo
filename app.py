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
    raise ValueError("DATABASE_URL environment variable not set. Please set it in your .env file or environment.")

try:
    client = MongoClient(MONGO_URI)
    db = client.Cluster0 # Asume que el nombre de la base de datos es 'Cluster0' de la URL proporcionada
    events_collection = db.events # Asume que la colección se llama 'events'
    startups_collection = db.startup # Asume que la colección de startups se llama 'startup'
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
def search_internet(query: str) -> str:
    """
    Realiza una búsqueda simulada en internet para la consulta dada.
    Simula el contenido de una página web o información relevante.
    """
    logging.info(f"Simulando búsqueda en internet para: {query}")
    # Simulación de contenido web basado en palabras clave en la query
    if "latitude59.ee" in query:
        return "El sitio web Latitude59.ee describe el evento Latitude 59 como la principal conferencia de startups y tecnología en los países bálticos. Se centra en la innovación, inversión, networking, y presenta pitches de startups de IA, SaaS, fintech y blockchain. Es un punto de encuentro para emprendedores, inversores y líderes tecnológicos."
    elif "slush.org" in query:
        return "El sitio web Slush.org presenta Slush como una de las conferencias de startups y tecnología más grandes del mundo, originaria de Helsinki. Se enfoca en la financiación de startups, el crecimiento empresarial, la conexión entre fundadores e inversores, y cubre temas como IA, sostenibilidad, deep tech y mercados emergentes."
    elif "websummit.com" in query:
        return "El sitio web WebSummit.com describe el Web Summit como 'la conferencia de tecnología más grande del mundo', que reúne a CEOs de Fortune 500, startups, inversores y periodistas. Cubre una amplia gama de temas tecnológicos, desde IA y software empresarial hasta impacto social y cultura tecnológica. Es un evento masivo de networking."
    elif "mwcbarcelona.com" in query:
        return "El sitio web MWCBarcelona.com es la página oficial del Mobile World Congress, la mayor feria mundial de la industria móvil. Se centra en la conectividad, 5G, IoT, IA móvil, realidad virtual/aumentada y hardware. Es un evento clave para empresas de telecomunicaciones y fabricantes de dispositivos."
    elif "techcrunch.com/events/disrupt" in query:
        return "El sitio web de TechCrunch Disrupt describe el evento como una plataforma para startups emergentes. Incluye el famoso 'Startup Battlefield' donde las startups compiten por financiación, charlas de líderes de la industria, y oportunidades de networking. Se centra en la innovación disruptiva en diversos sectores tecnológicos."
    elif "voicit.es" in query or "kimeratechnologies.com" in query: # Añadido el sitio de Kimera
        return "El sitio web de la startup se enfoca en soluciones de IA para el sector de eCommerce, específicamente en búsqueda y recomendación de productos mediante inteligencia artificial. Su tecnología SaaS ayuda a empresas B2B a mejorar la experiencia de compra online y la eficiencia operativa."
    elif "ia" in query.lower() or "inteligencia artificial" in query.lower():
        return "La Inteligencia Artificial (IA) es un campo de la informática que se enfoca en la creación de máquinas inteligentes que funcionan y reaccionan como humanos. Incluye aprendizaje automático (Machine Learning), procesamiento de lenguaje natural (NLP), visión por computadora y robótica. La IA está transformando industrias como RRHH y finanzas."
    elif "rrhh" in query.lower() or "recursos humanos" in query.lower():
        return "El sector de Recursos Humanos (RRHH) está experimentando una transformación digital. Las herramientas de IA en RRHH se utilizan para la automatización de procesos de contratación, análisis de talento, personalización de la experiencia del empleado y mejora de la eficiencia operativa. SaaS es un modelo común para estas soluciones."
    elif "saas" in query.lower() or "software como servicio" in query.lower():
        return "Software as a Service (SaaS) es un modelo de entrega de software donde el software es licenciado por suscripción y se aloja centralmente. Es una forma común de ofrecer aplicaciones empresariales y de consumo, proporcionando escalabilidad y accesibilidad. Muchas startups de IA operan bajo este modelo."
    else:
        return f"Resultados de búsqueda simulados para '{query}': Información general relevante para tecnología y startups."

# Define la herramienta para el modelo Gemini
search_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='search_internet',
            description='Performs a simulated internet search to get information about a website or a specific tech/startup topic.',
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
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[search_tool]
)

# --- Rutas de Flask ---

@app.route('/')
def index():
    """Sirve la página principal de la aplicación."""
    return render_template('index.html')

@app.route('/api/startups', methods=['GET'])
def get_startups():
    """
    Obtiene todos los nombres, descripciones, sectores y websites de startups de la base de datos.
    """
    try:
        startups_cursor = startups_collection.find({}, {'company': 1, 'description': 1, 'sector': 1, 'website': 1, '_id': 0})
        startups_list = []
        for startup in startups_cursor:
            startups_list.append(startup)
        logging.info(f"Startups encontradas: {len(startups_list)}")
        return jsonify(startups_list)
    except Exception as e:
        logging.error(f"Error al obtener startups: {e}")
        return jsonify({"error": "Fallo al obtener startups", "details": str(e)}), 500


@app.route('/api/event_names', methods=['GET'])
def get_event_names():
    """
    Obtiene todos los nombres únicos de eventos de la base de datos.
    """
    try:
        event_names = events_collection.distinct("name")
        sorted_names = sorted(event_names)
        logging.info(f"Nombres de eventos únicos encontrados: {len(sorted_names)}")
        return jsonify(sorted_names)
    except Exception as e:
        logging.error(f"Error al obtener nombres de eventos: {e}")
        return jsonify({"error": "Fallo al obtener nombres de eventos", "details": str(e)}), 500


@app.route('/api/events', methods=['GET'])
def get_events():
    """
    Obtiene eventos de la base de datos MongoDB, aplicando filtro por nombre de evento.
    Los parámetros de la URL son:
    - selectedEventName (string): Nombre del evento para filtrar.
    """
    selected_event_name = request.args.get('selectedEventName')

    query = {}
    if selected_event_name:
        query['name'] = selected_event_name

    try:
        events_cursor = events_collection.find(query)
        events_list = []
        for event in events_cursor:
            event['_id'] = str(event['_id'])
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
    - eventWebsite (string): URL del sitio web del evento.
    - startupName (string): Nombre de la startup del usuario.
    - startupDescription (string): Descripción de la startup del usuario.
    - startupSector (string): Sector de la startup del usuario.
    - startupWebsite (string): URL del sitio web de la startup del usuario.
    """
    try:
        data = request.json
        event_name = data.get('eventName')
        event_website = data.get('eventWebsite')
        startup_name = data.get('startupName')
        startup_description = data.get('startupDescription')
        startup_sector = data.get('startupSector')
        startup_website = data.get('startupWebsite')

        logging.info(f"Recibida solicitud de análisis de Gemini para: Evento={event_name}, URL Evento={event_website}, Startup={startup_name}, Desc={startup_description}, Sector={startup_sector}, URL Startup={startup_website}")

        if not all([event_name, event_website, startup_name, startup_description, startup_sector, startup_website]):
            logging.warning("Solicitud de análisis de Gemini incompleta: faltan datos.")
            return jsonify({"error": "Faltan datos en la solicitud para el análisis de Gemini."}), 400

        # Obtener todos los eventos para que Gemini pueda recomendar
        all_events_for_gemini = []
        try:
            events_cursor = events_collection.find({})
            for event in events_cursor:
                all_events_for_gemini.append({
                    "name": event.get("name"),
                    "description": event.get("description", "No hay descripción disponible."),
                    "location": event.get("location"),
                    "initialDate": event.get("initialDate").isoformat() if isinstance(event.get("initialDate"), datetime) else None,
                    "finalDate": event.get("finalDate").isoformat() if isinstance(event.get("finalDate"), datetime) else None,
                    "website": event.get("website")
                })
        except Exception as e:
            logging.error(f"Error al obtener todos los eventos para Gemini (para recomendación): {e}")

        events_list_str = "\n".join([
            f"- Nombre: {e['name']}, Descripción: {e['description']}, Ubicación: {e['location']}, Fechas: {e['initialDate']} a {e['finalDate']}"
            for e in all_events_for_gemini if e['name'] != event_name
        ])

        prompt = f"""
        Eres un asistente experto en el ecosistema de eventos de tecnología y startups. Tu tarea es analizar un evento específico y la información detallada de una startup, y determinar si el evento es de interés para esa startup. Si no lo es, debes recomendar otro evento de una lista proporcionada.

        Aquí tienes la información clave:
        - Nombre de la startup actual: "{startup_name}"
        - Descripción de la Startup del Usuario: "{startup_description}"
        - Sector de la Startup del Usuario: "{startup_sector}"
        - URL del Sitio Web de la Startup: "{startup_website}"
        - Nombre del Evento Actual: "{event_name}"
        - URL del Sitio Web del Evento Actual: "{event_website}"

        **Paso 1: Investigación Contextual.**
        Usa la herramienta `search_internet` con la URL del sitio web del evento actual ("{event_website}") para obtener una comprensión de su temática, enfoque y audiencia. Haz lo mismo con la URL del sitio web de la startup seleccionada ("{startup_website}") para entender mejor sus productos, servicios y propuesta de valor.

        **Paso 2: Evaluación de Interés.**
        Basado en la información recopilada de ambos sitios web (evento y startup), la descripción de la startup y su sector, determina si el evento actual es de interés para la startup "{startup_name}". Considera si el evento ofrece oportunidades de networking, visibilidad para soluciones en su sector (IA, RRHH, SaaS), posibles clientes, inversores, o conocimiento relevante para su crecimiento.

        **Paso 3: Generación de Respuesta.**
        Crea una respuesta concisa de aproximadamente 100 palabras (unos 500-700 caracteres).

        **Si el evento es de interés para la startup:**
        Explica claramente por qué ese evento es relevante para la startup "{startup_name}", destacando los beneficios específicos que podría obtener al asistir o participar.

        **Si el evento NO es de interés (o es menos relevante) para la startup:**
        Explica por qué no se alinea bien con los objetivos de "{startup_name}". Luego, **recomienda un evento alternativo** de la siguiente lista de eventos disponibles que crees que sería más adecuado para la startup, y justifica tu recomendación. Si no hay otros eventos adecuados, indícalo.

        **Lista de Otros Eventos Disponibles para Recomendación (si aplica):**
        {events_list_str if events_list_str else "No hay otros eventos disponibles para recomendar."}

        **Formato de la Respuesta:**
        - Si es de interés: "¡Este evento es muy prometedor para {startup_name}! [Explicación detallada de por qué, mencionando la relación con IA, RRHH, SaaS, networking, etc. Máx. ~100 palabras]"
        - Si NO es de interés: "Este evento parece menos alineado con los objetivos de {startup_name}. [Explicación concisa y recomendación de un evento alternativo de la lista, justificando por qué es mejor. Máx. ~100 palabras]"
        """

        logging.info("Enviando prompt a Gemini...")
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        logging.info(f"Respuesta inicial de Gemini recibida: {response}")

        # Lista para almacenar todas las partes de la respuesta de la herramienta
        tool_responses_parts = []

        # Bucle para procesar múltiples llamadas a herramientas si Gemini las hace
        while True:
            # Comprobar si hay candidatos y si el primer candidato tiene contenido y partes
            if not (response.candidates and len(response.candidates) > 0 and \
                    response.candidates[0].content and len(response.candidates[0].content.parts) > 0):
                logging.warning(f"Respuesta de Gemini no tiene la estructura esperada de candidatos/contenido/partes. Saliendo del bucle de herramienta. Respuesta completa: {response}")
                break # Salir si la estructura básica no está presente o no hay más llamadas a herramientas

            function_call_found_in_this_turn = False
            current_turn_function_calls = []

            # Recopilar todas las llamadas a funciones en el turno actual
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    current_turn_function_calls.append(part.function_call)
                    function_call_found_in_this_turn = True
            
            if not function_call_found_in_this_turn:
                break # Si no se encontró ninguna llamada a función en las partes, salir del bucle

            # Ejecutar cada llamada a función y recopilar sus respuestas
            for call in current_turn_function_calls:
                logging.info(f"Gemini solicitó llamada a herramienta: {call.name} con args: {call.args}")
                if call.name == 'search_internet':
                    tool_response_content = search_internet(call.args['query'])
                    logging.info(f"Respuesta de la herramienta search_internet: {tool_response_content}")
                    tool_responses_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name='search_internet',
                                response={
                                    'result': tool_response_content
                                }
                            )
                        )
                    )
                else:
                    logging.warning(f"Llamada a herramienta no reconocida: {call.name}")
                    tool_responses_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=call.name,
                                response={
                                    'error': 'Herramienta no reconocida o no implementada.'
                                }
                            )
                        )
                    )
            
            # Enviar TODAS las respuestas de las herramientas de vuelta a Gemini en un solo mensaje
            logging.info(f"Enviando {len(tool_responses_parts)} respuestas de herramientas de vuelta a Gemini.")
            response = chat.send_message(tool_responses_parts)
            tool_responses_parts = [] # Limpiar para el siguiente turno si hubiera
            logging.info(f"Respuesta de Gemini después de enviar respuestas de herramientas: {response}")

        # Después de que todas las llamadas a herramientas hayan sido procesadas o si no hubo ninguna
        if response.candidates and len(response.candidates) > 0 and \
           response.candidates[0].content and len(response.candidates[0].content.parts) > 0 and \
           response.candidates[0].content.parts[0].text: # Asegurarse de que el campo 'text' existe
            
            gemini_output = response.candidates[0].content.parts[0].text
            # Truncar la salida a aproximadamente 100 palabras (aprox. 500-700 caracteres para español)
            if len(gemini_output) > 700: # Limite de caracteres para ~100 palabras
                gemini_output = gemini_output[:697] + "..."
            logging.info(f"Análisis final de Gemini generado para '{event_name}': {gemini_output}")
            return jsonify({"analysis": gemini_output})
        else:
            logging.warning(f"Gemini no devolvió una respuesta de texto válida para '{event_name}' en la fase final. Respuesta completa: {response}")
            return jsonify({"error": "Gemini no pudo generar un análisis válido. Inténtalo de nuevo. Revisa los logs del servidor para más detalles."}), 500

    except Exception as e:
        logging.error(f"Error inesperado al llamar a la API de Gemini para '{event_name}': {e}", exc_info=True)
        return jsonify({"error": "Fallo al obtener el análisis de Gemini", "details": str(e)}), 500

# --- Lógica de Inserción de Datos de Prueba (Solo para desarrollo/primera ejecución) ---
if __name__ == '__main__':
    try:
        if events_collection.count_documents({}) == 0:
            logging.info("No se encontraron eventos en la base de datos. Insertando datos de prueba de eventos...")
            dummy_events = [
                {
                    "id": "687bbf5995aa2580f6dec88e",
                    "name": "Latitude 59",
                    "initialDate": datetime(2025, 5, 21, 0, 0, 0),
                    "finalDate": datetime(2025, 5, 23, 0, 0, 0),
                    "location": "Tallinn",
                    "website": "https://latitude59.ee/",
                    "description": "Startup InnovaTech es una empresa de IA que desarrolla soluciones de procesamiento de lenguaje natural para el sector financiero, enfocándose en la automatización de análisis de mercado y detección de fraudes."
                },
                {
                    "id": "a1b2c3d4e5f6g7h8i9j0k1l2",
                    "name": "Slush",
                    "initialDate": datetime(2025, 11, 30, 0, 0, 0),
                    "finalDate": datetime(2025, 12, 1, 0, 0, 0),
                    "location": "Helsinki",
                    "website": "https://www.slush.org/",
                    "description": "CryptoLedger Solutions crea soluciones de blockchain para la gestión de la cadena de suministro, enfocándose en la trazabilidad y la transparencia de productos agrícolas desde la granja hasta el consumidor."
                },
                {
                    "id": "m3n4o5p6q7r8s9t0u1v2w3x4",
                    "name": "Web Summit",
                    "initialDate": datetime(2025, 11, 11, 0, 0, 0),
                    "finalDate": datetime(2025, 11, 14, 0, 0, 0),
                    "location": "Lisbon",
                    "website": "https://websummit.com/",
                    "description": "CloudConnect Global es una plataforma SaaS que optimiza la colaboración remota para equipos distribuidos, integrando herramientas de comunicación, gestión de proyectos y compartición de documentos para mejorar la productividad empresarial."
                },
                {
                    "id": "y5z6a7b8c9d0e1f2g3h4i5j6",
                    "name": "Mobile World Congress",
                    "initialDate": datetime(2026, 2, 24, 0, 0, 0),
                    "finalDate": datetime(2026, 2, 27, 0, 0, 0),
                    "location": "Barcelona",
                    "website": "https://www.mwcbarcelona.com/",
                    "description": "NextGen IoT desarrolla hardware y software para la próxima generación de redes 5G y soluciones IoT, con un enfoque en ciudades inteligentes y optimización del consumo energético en entornos urbanos."
                },
                {
                    "id": "z7x8c9v0b1n2m3l4k5j6h7g8",
                    "name": "TechCrunch Disrupt",
                    "initialDate": datetime(2025, 9, 15, 0, 0, 0),
                    "finalDate": datetime(2025, 9, 17, 0, 0, 0),
                    "location": "San Francisco",
                    "website": "https://techcrunch.com/events/disrupt/",
                    "description": "BioMed Innovations es una startup de biotecnología que utiliza IA para acelerar el descubrimiento de fármacos y personalizar tratamientos médicos, con un enfoque en enfermedades raras."
                }
            ]
            try:
                events_collection.insert_many(dummy_events)
                logging.info(f"Se insertaron {len(dummy_events)} datos de prueba de eventos con éxito.")
            except Exception as e:
                logging.error(f"Error al insertar datos de prueba de eventos: {e}")
        else:
            logging.info("La base de datos ya contiene eventos. No se insertaron datos de prueba de eventos.")
    except Exception as e:
        logging.error(f"Error al verificar la colección de eventos: {e}")

    # --- Lógica de Inserción de Datos de Prueba para Startups ---
    try:
        if startups_collection.count_documents({}) == 0:
            logging.info("No se encontraron startups en la base de datos. Insertando datos de prueba de startups...")
            dummy_startups = [
                {
                    "company": "Voicit",
                    "description": "Voicit es la herramienta basada en IA para consultoras de RRHH",
                    "sector": "RRHH, IA, SaaS",
                    "website": "https://voicit.es/"
                },
                {
                    "company": "InnovateX",
                    "description": "Plataforma de gestión de proyectos con IA para equipos de desarrollo de software.",
                    "sector": "Software, IA, Gestión de Proyectos",
                    "website": "https://innovatex.com/"
                },
                {
                    "company": "GreenEnergy Solutions",
                    "description": "Desarrolla soluciones de energía renovable y optimización de consumo energético para ciudades inteligentes.",
                    "sector": "Energía, Sostenibilidad, IoT",
                    "website": "https://greenenergysolutions.com/"
                },
                {
                    "company": "FinTech Flow",
                    "description": "Aplicación de finanzas personales que utiliza blockchain para transacciones seguras y transparentes.",
                    "sector": "Fintech, Blockchain, Finanzas",
                    "website": "https://fintechflow.com/"
                },
                {
                    "company": "Kimera",
                    "description": "Kimera es un SaaS B2B para la búsqueda y recomendación de productos eCommerce mediante tecnologías de IA.",
                    "sector": "Software, IA, eCommerce",
                    "website": "https://kimeratechnologies.com/"
                }
            ]
            try:
                startups_collection.insert_many(dummy_startups)
                logging.info(f"Se insertaron {len(dummy_startups)} datos de prueba de startups con éxito.")
            except Exception as e:
                logging.error(f"Error al insertar datos de prueba de startups: {e}")
        else:
            logging.info("La base de datos ya contiene startups. No se insertaron datos de prueba de startups.")
    except Exception as e:
        logging.error(f"Error al verificar la colección de startups: {e}")


    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))













