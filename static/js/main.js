// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // Inicialización del mapa Leaflet
    const map = L.map('map').setView([40.4168, -3.7038], 5); // Centrado inicial en España

    // Añadir capa de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let markers = []; // Array para almacenar los marcadores actuales en el mapa

    const eventDateFilter = document.getElementById('eventDateFilter');
    const filterBtn = document.getElementById('filterBtn');
    const resetBtn = document.getElementById('resetBtn');
    const geminiAnalysisDiv = document.getElementById('geminiAnalysis');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // Descripción de la startup del usuario (hardcodeada para este ejemplo)
    const userStartupDescription = "Voicit es la herramienta basada en IA para consultoras de RRHH";

    /**
     * Limpia todos los marcadores existentes del mapa.
     */
    function clearMarkers() {
        markers.forEach(marker => marker.remove());
        markers = [];
    }

    /**
     * Formatea una fecha ISO (ej. 2025-05-21) a un formato legible (ej. 21/05/2025).
     * @param {string} isoDateString La cadena de fecha en formato ISO (YYYY-MM-DD).
     * @returns {string} La fecha formateada.
     */
    function formatDateDisplay(isoDateString) {
        if (!isoDateString) return 'N/A';
        try {
            const [year, month, day] = isoDateString.split('-');
            const date = new Date(year, month - 1, day);
            return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
        } catch (e) {
            console.error("Error al formatear la fecha para mostrar:", isoDateString, e);
            return isoDateString;
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
            geminiAnalysisDiv.appendChild(loadingIndicator);
        } else {
            loadingIndicator.classList.add('hidden');
        }
    }

    /**
     * Rellena el desplegable de fechas con las fechas de eventos únicas desde el backend.
     */
    async function populateDateFilterDropdown() {
        try {
            const response = await fetch('/api/event_dates');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Fallo al cargar las fechas de eventos');
            }
            const dates = await response.json();

            eventDateFilter.innerHTML = '<option value="">Todos los eventos</option>';

            dates.forEach(dateStr => {
                const option = document.createElement('option');
                option.value = dateStr;
                option.textContent = formatDateDisplay(dateStr);
                eventDateFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Error al cargar las fechas para el desplegable:', error);
            displayGeminiAnalysis(`Error al cargar las fechas de eventos: ${error.message}.`);
        }
    }

    /**
     * Obtiene y muestra los eventos en el mapa.
     * @param {string} selectedDate Fecha seleccionada del desplegable (formato YYYY-MM-DD).
     */
    async function fetchAndDisplayEvents(selectedDate = '') {
        clearMarkers();
        const params = new URLSearchParams();
        if (selectedDate) {
            params.append('selectedDate', selectedDate);
        }

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
                if (event.location_point && Array.isArray(event.location_point.coordinates) && event.location_point.coordinates.length === 2) {
                    const [longitude, latitude] = event.location_point.coordinates;
                    const marker = L.marker([latitude, longitude]).addTo(map);

                    const popupContent = `
                        <div class="font-inter">
                            <h3 class="text-lg font-bold text-indigo-700 mb-1">${event.name}</h3>
                            <p class="text-sm text-gray-700"><strong>Fecha:</strong> ${formatDateDisplay(event.initialDate.split('T')[0])} - ${formatDateDisplay(event.finalDate.split('T')[0])}</p>
                            <p class="text-sm text-gray-700"><strong>Ubicación:</strong> ${event.location}</p>
                            <p class="text-sm text-gray-700 mb-2">
                                <a href="${event.website}" target="_blank" class="text-indigo-600 hover:underline">Visitar sitio web</a>
                            </p>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                    markers.push(marker);

                    // Activar el análisis de Gemini al abrir el popup
                    marker.on('popupopen', async function() {
                        displayGeminiAnalysis("Cargando análisis de Gemini...", true);

                        try {
                            const geminiResponse = await fetch('/api/gemini_analysis', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    eventName: event.name,
                                    eventWebsite: event.website, // Pasar la URL del evento
                                    startupDescription: userStartupDescription // Pasar la descripción de la startup del usuario
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
                    });
                } else {
                    console.warn(`Evento ${event.name} no tiene coordenadas válidas:`, event.location_point);
                }
            });

            if (markers.length > 0) {
                const group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.5));
            } else {
                map.setView([40.4168, -3.7038], 5);
            }

        } catch (error) {
            console.error('Error al cargar los eventos:', error);
            displayGeminiAnalysis(`Error al cargar los eventos: ${error.message}. Por favor, verifica la conexión con el servidor y la consola del navegador para más detalles.`);
        }
    }

    // --- Event Listeners ---
    filterBtn.addEventListener('click', () => {
        const selectedDate = eventDateFilter.value;
        fetchAndDisplayEvents(selectedDate);
    });

    resetBtn.addEventListener('click', () => {
        eventDateFilter.value = ''; // Seleccionar la opción "Todos los eventos"
        displayGeminiAnalysis("Haz clic en un marcador de evento en el mapa para obtener un análisis de Gemini sobre su relevancia para tus intereses en startups y tecnología.");
        fetchAndDisplayEvents(); // Carga todos los eventos sin filtros
    });

    // Cargar las fechas en el desplegable y luego cargar todos los eventos al inicio
    populateDateFilterDropdown().then(() => {
        fetchAndDisplayEvents();
    });
});

