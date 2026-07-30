function Calendario(opts) {
    var el = document.getElementById(opts.container);
    if (!el) return;

    var initialYear = opts.year;
    var initialMonth = opts.month;
    if (!initialYear && opts.selectedYear) initialYear = opts.selectedYear;
    if (!initialMonth && opts.selectedMonth) initialMonth = opts.selectedMonth;

    var state = {
        year: initialYear || new Date().getFullYear(),
        month: initialMonth || new Date().getMonth() + 1,
        diasConEntrenos: [],
        diasConCompeticion: [],
        selectedDay: opts.selectedDay || null,
        selectedMonth: opts.selectedMonth || null,
        selectedYear: opts.selectedYear || null,
        onDiaClick: opts.onDiaClick || function() {}
    };

    var months = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ];

    var dayNames = ["Lu","Ma","Mi","Ju","Vi","Sa","Do"];

    function render() {
        var today = new Date();
        var todayStr = today.getFullYear() + "-" + (today.getMonth()+1) + "-" + today.getDate();

        var firstDay = new Date(state.year, state.month - 1, 1);
        var lastDay = new Date(state.year, state.month, 0);
        var numDays = lastDay.getDate();
        var startWeekday = (firstDay.getDay() + 6) % 7;

        var html = '<div class="cal-nav">';
        html += '<button class="cal-btn" data-action="prev">◀</button>';
        html += '<span class="cal-title">' + months[state.month - 1] + '</span>';
        html += '<input type="number" class="cal-year" value="' + state.year + '" min="2020" max="2035">';
        html += '<button class="cal-btn" data-action="next">▶</button>';
        html += '</div>';

        html += '<div class="cal-grid">';
        for (var i = 0; i < 7; i++) {
            html += '<div class="cal-day-header">' + dayNames[i] + '</div>';
        }

        for (var i = 0; i < startWeekday; i++) {
            html += '<div class="cal-day cal-day--empty"></div>';
        }

        for (var d = 1; d <= numDays; d++) {
            var dateStr = state.year + "-" + state.month + "-" + d;
            var classes = ["cal-day"];
            if (state.diasConEntrenos.indexOf(d) !== -1) {
                classes.push("cal-day--has-data");
            }
            if (state.diasConCompeticion.indexOf(d) !== -1) {
                classes.push("cal-day--has-competencia");
            }
            if (dateStr === todayStr) {
                classes.push("cal-day--today");
            }
            if (
                state.selectedDay === d
                && state.selectedMonth === state.month
                && state.selectedYear === state.year
            ) {
                classes.push("cal-day--selected");
            }
            var clickHandler = '';
            html += '<div class="' + classes.join(" ") + '" data-day="' + d + '">' + d + '</div>';
        }

        html += '</div>';
        el.innerHTML = html;

        el.querySelector(".cal-nav").addEventListener("click", function(e) {
            var btn = e.target.closest("[data-action]");
            if (!btn) return;
            var action = btn.getAttribute("data-action");
            if (action === "prev") {
                state.month--;
                if (state.month < 1) { state.month = 12; state.year--; }
                el.querySelector(".cal-year").value = state.year;
                load();
            } else if (action === "next") {
                state.month++;
                if (state.month > 12) { state.month = 1; state.year++; }
                el.querySelector(".cal-year").value = state.year;
                load();
            }
        });

        el.querySelector(".cal-year").addEventListener("change", function() {
            var val = parseInt(this.value);
            if (val && val >= 2020 && val <= 2035) {
                state.year = val;
                load();
            }
        });

        el.querySelectorAll(".cal-day--has-data").forEach(function(dayEl) {
            dayEl.addEventListener("click", function() {
                state.onDiaClick(parseInt(this.getAttribute("data-day")), state.month, state.year);
            });
        });
    }

    function load() {
        fetch("/registros/dias?year=" + state.year + "&month=" + state.month)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                state.diasConEntrenos = data.dias || [];
                state.diasConCompeticion = data.dias_competicion || [];
                render();
            })
            .catch(function() { render(); });
    }

    load();
}
