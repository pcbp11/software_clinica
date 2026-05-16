document.addEventListener('DOMContentLoaded', function () {
    const servicioField = document.querySelector('#id_servicio');
    const montoTotalField = document.querySelector('#id_monto_total');

    if (servicioField) {
        servicioField.addEventListener('change', function () {
            fetch(`/admin/core/servicio/${servicioField.value}/change/`)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const precioInput = doc.querySelector('#id_precio');

                    if (precioInput && montoTotalField) {
                        montoTotalField.value = precioInput.value;
                    }
                });
        });
    }
});