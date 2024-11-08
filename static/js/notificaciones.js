class NotificacionesManager {
    constructor() {
        this.socket = null;
        this.notificacionesContainer = document.getElementById('notificaciones-dropdown');
        this.contadorNotificaciones = document.getElementById('contador-notificaciones');
        this.setupWebSocket();
        this.setupNotificationSound();
    }

    setupWebSocket() {
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/notificaciones/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.mostrarNotificacion(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket desconectado. Reconectando en 5 segundos...');
            setTimeout(() => this.setupWebSocket(), 5000);
        };
    }

    setupNotificationSound() {
        this.notificationSound = new Audio('/static/sounds/notification.mp3');
    }

    mostrarNotificacion(data) {
        // Mostrar notificación del navegador si está permitido
        if (Notification.permission === 'granted') {
            new Notification(data.titulo, {
                body: data.mensaje,
                icon: '/static/img/logo.png'
            });
        }

        // Reproducir sonido
        this.notificationSound.play().catch(e => console.log('Error al reproducir sonido:', e));

        // Crear elemento de notificación
        const notificacionHTML = `
            <div class="dropdown-item notification-item" data-id="${data.id}">
                <div class="d-flex align-items-center">
                    <div class="flex-shrink-0">
                        <i class="fas fa-bell text-primary"></i>
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <h6 class="mb-0">${data.titulo}</h6>
                        <small class="text-muted">${data.mensaje}</small>
                        <div class="text-muted mt-1" style="font-size: 0.75rem;">
                            ${this.formatearFecha(data.fecha)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insertar al principio del contenedor
        this.notificacionesContainer.insertAdjacentHTML('afterbegin', notificacionHTML);

        // Actualizar contador
        this.actualizarContador(1);

        // Mostrar toast
        this.mostrarToast(data);
    }

    actualizarContador(incremento = 0) {
        let contador = parseInt(this.contadorNotificaciones.textContent || '0');
        contador += incremento;
        
        if (contador > 0) {
            this.contadorNotificaciones.textContent = contador;
            this.contadorNotificaciones.classList.remove('d-none');
        } else {
            this.contadorNotificaciones.classList.add('d-none');
        }
    }

    mostrarToast(data) {
        const toastEl = document.getElementById('notificacionToast');
        if (toastEl) {
            const toast = new bootstrap.Toast(toastEl);
            document.getElementById('notificacionToastTitulo').textContent = data.titulo;
            document.getElementById('notificacionToastMensaje').textContent = data.mensaje;
            toast.show();
        }
    }

    formatearFecha(fecha) {
        const date = new Date(fecha);
        return date.toLocaleString();
    }

    marcarComoLeida(notificacionId) {
        fetch(`/usuarios/notificaciones/${notificacionId}/leida/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.actualizarContador(-1);
            }
        });
    }

    marcarTodasComoLeidas() {
        fetch('/usuarios/notificaciones/marcar-todas-leidas/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelectorAll('.notification-item.unread').forEach(item => {
                    item.classList.remove('unread');
                });
                this.contadorNotificaciones.classList.add('d-none');
            }
        });
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}

// Inicializar cuando el documento esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Solicitar permiso para notificaciones del navegador
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }

    // Inicializar manager de notificaciones
    window.notificacionesManager = new NotificacionesManager();
});
