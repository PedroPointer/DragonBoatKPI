$(document).ready(function() {
    var table = $("#tabla-registros").DataTable({
        order: [[6, "desc"], [0, "asc"]],
        pageLength: 50,
        scrollX: true,
        autoWidth: false,
        language: {
            url: "//cdn.datatables.net/plug-ins/1.13.11/i18n/es-ES.json"
        },
        columnDefs: [
            { type: "num", targets: 0 },
            { type: "num", targets: 4 },
            { type: "date-eu", targets: 6 },
            { targets: [7], orderable: false },
            { targets: [8], orderable: false, searchable: false }
        ]
    });

    var activeFilter = { day: null, month: null, year: null };

    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
        if (!activeFilter.day) return true;
        var fecha = data[6];
        var parts = fecha.split("/");
        var rowDay = parseInt(parts[0]);
        var rowMonth = parseInt(parts[1]);
        var rowYear = parseInt(parts[2]);
        return (rowDay === activeFilter.day &&
                rowMonth === activeFilter.month &&
                rowYear === activeFilter.year);
    });

    window.filtrarPorDia = function(day, month, year) {
        activeFilter.day = day;
        activeFilter.month = month;
        activeFilter.year = year;
        table.draw();
    };

    window.limpiarFiltros = function() {
        activeFilter.day = null;
        activeFilter.month = null;
        activeFilter.year = null;
        table.search("").columns().search("").draw();
    };
});
