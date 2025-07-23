// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // Inicialización del mapa Leaflet
    const map = L.map('map').setView([40.4168, -3.7038], 5); // Centrado inicial en España

    // Añadir capa de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let markers = []; // Array para almacenar los marcadores actuales en el mapa

    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const locationInput = document.getElementById('location');
    const filterBtn = document.getElementById('filterBtn');
    const resetBtn = document.getElementById('resetBtn');
    const geminiAnalysisDiv = document.getElementById('geminiAnalysis');
    const loadingIndicator = document.getElementById('loadingIndicator');

    /**
     * Limpia todos los marcadores existentes del mapa.
     */
    function clearMarkers() {
        markers.forEach(marker => marker.remove());
        markers = [];
    }

    /**
     * Formatea una fecha ISO (ej. 2025-05-21T00:00:00Z) a un formato legible (ej. 21/05/2025).
     * @param {string} isoDateString La cadena de fecha en formato ISO.
     * @returns {string} La fecha formateada.
     */
    function formatDate(isoDateString) {
        if (!isoDateString) return 'N/A';
        try {
            const date = new Date(isoDateString);
            return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (e) {
            console.error("Error al formatear la fecha:", isoDateString, e);
            return isoDateString; // Retorna la original si hay error
        }
    }

    /**
     * Muestra un mensaje en el panel de análisis de Gemini.
     * @param {string} message El mensaje a mostrar.
     * @param {boolean} isLoading Si es true, muestra el indicador de carga.
     */
    function displayGeminiAnalysis(message, isLoading = false) {
        geminiAnalysisDiv.innerHTML = `<p>${message}</p>`;
        if (isLoading) {
            loadingIndicator.classList.remove('hidden');
            geminiAnalysisDiv.appendChild(loadingIndicator); // Asegura que el indicador esté dentro
        } else {
            loadingIndicator.classList.add('hidden');
        }
    }

    /**
     * Obtiene y muestra los eventos en el mapa.
     * @param {string} startDate Fecha de inicio para filtrar (formato YYYY-MM-DD).
     * @param {string} endDate Fecha de fin para filtrar (formato YYYY-MM-DD).
     * @param {string} location Ubicación para filtrar.
     */
    async function fetchAndDisplayEvents(startDate = '', endDate = '', location = '') {
        clearMarkers();
        const params = new URLSearchParams();
        if (startDate) params.append('startDate', `${startDate}T00:00:00Z`);
        if (endDate) params.append('endDate', `${endDate}T23:59:59Z`); // Fin del día
        if (location) params.append('location', location);

        try {
            const response = await fetch(`/api/events?${params.toString()}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Fallo al cargar los eventos');
            }
            const events = await response.json();

            if (events.length === 0) {
                displayGeminiAnalysis("No se encontraron eventos con los filtros aplicados. Intenta ajustar tus criterios.");
                return;
            }

            events.forEach(event => {
                // Las coordenadas de MongoDB son [longitud, latitud]. Leaflet usa [latitud, longitud].
                // Asegúrate de que event.location_point.coordinates existe y tiene 2 elementos.
                if (event.location_point && Array.isArray(event.location_point.coordinates) && event.location_point.coordinates.length === 2) {
                    const [longitude, latitude] = event.location_point.coordinates;
                    const marker = L.marker([latitude, longitude]).addTo(map);

                    // Contenido del popup
                    const popupContent = `
                        <div class="font-inter">
                            <h3 class="text-lg font-bold text-indigo-700 mb-1">${event.name}</h3>
                            <p class="text-sm text-gray-700"><strong>Fecha:</strong> ${formatDate(event.initialDate)} - ${formatDate(event.finalDate)}</p>
                            <p class="text-sm text-gray-700"><strong>Ubicación:</strong> ${event.location}</p>
                            <p class="text-sm text-gray-700 mb-2">
                                <a href="${event.website}" target="_blank" class="text-indigo-600 hover:underline">Visitar sitio web</a>
                            </p>
                            <button class="analyze-btn bg-indigo-500 text-white text-xs py-1 px-3 rounded-md hover:bg-indigo-600 transition duration-150 ease-in-out shadow-sm"
                                data-event-name="${event.name}"
                                data-startup-description="${event.description || 'No hay descripción de startup disponible.'}"
                                data-event-theme="${event.theme || 'tecnología y startups'}"
                            >
                                Analizar con Gemini
                            </button>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                    markers.push(marker);

                    // Añadir listener al botón dentro del popup cuando se abre
                    marker.on('popupopen', function() {
                        const btn = document.querySelector('.leaflet-popup-content .analyze-btn');
                        if (btn) {
                            btn.onclick = async () => {
                                const eventName = btn.dataset.eventName;
                                const startupDescription = btn.dataset.startupDescription;
                                const eventTheme = btn.dataset.eventTheme;

                                displayGeminiAnalysis("Cargando análisis de Gemini...", true);

                                try {
                                    const geminiResponse = await fetch('/api/gemini_analysis', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                        },
                                        body: JSON.stringify({
                                            eventName: eventName,
                                            startupDescription: startupDescription,
                                            eventTheme: eventTheme
                                        }),
                                    });

                                    if (!geminiResponse.ok) {
                                        const errorData = await geminiResponse.json();
                                        throw new Error(errorData.error || 'Fallo al obtener el análisis de Gemini');
                                    }

                                    const data = await geminiResponse.json();
                                    displayGeminiAnalysis(data.analysis);
                                } catch (error) {
                                    console.error('Error al obtener el análisis de Gemini:', error);
                                    displayGeminiAnalysis(`Error al obtener el análisis: ${error.message}. Inténtalo de nuevo.`);
                                }
                            };
                        }
                    });
                } else {
                    console.warn(`Evento ${event.name} no tiene coordenadas válidas:`, event.location_point);
                }
            });

            // Ajustar el mapa para que muestre todos los marcadores
            if (markers.length > 0) {
                const group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.5)); // Añade un poco de padding
            } else {
                // Si no hay marcadores, restablece la vista a la inicial
                map.setView([40.4168, -3.7038], 5);
            }

        } catch (error) {
            console.error('Error al cargar los eventos:', error);
            displayGeminiAnalysis(`Error al cargar los eventos: ${error.message}. Por favor, verifica la conexión.`);
        }
    }

    // --- Event Listeners ---
    filterBtn.addEventListener('click', () => {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const location = locationInput.value;
        fetchAndDisplayEvents(startDate, endDate, location);
    });

    resetBtn.addEventListener('click', () => {
        startDateInput.value = '';
        endDateInput.value = '';
        locationInput.value = '';
        displayGeminiAnalysis("Haz clic en un marcador de evento en el mapa para obtener un análisis de Gemini sobre su relevancia para tus intereses en startups y tecnología.");
        fetchAndDisplayEvents(); // Carga todos los eventos sin filtros
    });

    // Cargar todos los eventos al inicio
    fetchAndDisplayEvents();
});
