/* =========================================================
   REPORTES.JS - PANEL DE REPORTES
   Sistema de Inscripciones - UE Jesús María
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
  initReportTabs();
  initAjaxReports();
  initPrintButtons();
  initReportAnimations();
  initCourseExpand();
  switchReport("reporte-estudiantes");
});

const REPORT_COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#6366f1",
  "#84cc16",
  "#06b6d4",
  "#d946ef",
];

let chartsInitialized = false;


function initReportTabs() {
  const tabs = document.querySelectorAll(".reports-tabs .tab");

  tabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      const target = this.dataset.tab;

      if (!target) return;

      switchReport(target);
    });
  });
}


function switchReport(id) {
  const tabs = document.querySelectorAll(".reports-tabs .tab");
  const contents = document.querySelectorAll(".reports-content .accordion-content");

  tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === id;

    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  contents.forEach((content) => {
    content.classList.remove("open");
  });

  const activeContent = document.getElementById(id);

  if (activeContent) {
    activeContent.classList.add("open");
  }

  if (id === "reporte-academico") {
    initCharts();
  }
}


function initAjaxReports() {
  bindAjaxReport("reporte-estudiantes", ".filter-bar", ".pagination a, a[data-ajax]");
  bindAjaxReport("reporte-inscripciones", ".filter-bar", ".pagination a, a[data-ajax-ins]");
  bindAjaxReport("reporte-documental", ".filter-bar", ".pagination a, a[data-ajax-doc]");
  bindAjaxReport("reporte-cursos", ".courses-filter-form", "a[data-ajax-cur]");
}


function bindAjaxReport(reportId, formSelector, linkSelector) {
  const report = document.getElementById(reportId);

  if (!report) return;

  report.addEventListener("submit", function (event) {
    const form = event.target.closest(formSelector);

    if (!form) return;

    event.preventDefault();

    const url = new URL(form.action || window.location.href);
    url.search = new URLSearchParams(new FormData(form)).toString();

    loadReport(url, reportId);
  });

  report.addEventListener("click", function (event) {
    const link = event.target.closest(linkSelector);

    if (!link) return;

    event.preventDefault();

    loadReport(new URL(link.href), reportId);
  });
}


function loadReport(url, reportId) {
  const currentReport = document.getElementById(reportId);

  if (!currentReport) return;

  currentReport.classList.add("report-loading");

  url.hash = reportId;

  fetch(url, {
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("No se pudo cargar el reporte.");
      }

      return response.text();
    })
    .then((html) => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const newReport = doc.querySelector(`#${reportId}`);

      if (newReport) {
        currentReport.innerHTML = newReport.innerHTML;
      }

      window.history.pushState({}, "", url.toString());
      switchReport(reportId);
    })
    .catch(() => {
      showReportError();
    })
    .finally(() => {
      currentReport.classList.remove("report-loading");
    });
}


function showReportError() {
  if (typeof Swal === "undefined") {
    alert("No se pudo cargar el reporte. Intente nuevamente.");
    return;
  }

  Swal.fire({
    title: "Error al cargar reporte",
    text: "No se pudo actualizar la información del reporte.",
    icon: "error",
    confirmButtonColor: "#c62828",
    confirmButtonText: "Entendido",
  });
}


function getJsonScript(id, fallback = []) {
  const element = document.getElementById(id);

  if (!element) return fallback;

  try {
    return JSON.parse(element.textContent);
  } catch (error) {
    return fallback;
  }
}


function initCharts() {
  if (chartsInitialized) return;
  if (typeof Chart === "undefined") return;

  chartsInitialized = true;

  const dataNiveles = {
    labels: getJsonScript("dataNivelesLabels"),
    values: getJsonScript("dataNivelesValues"),
  };

  const dataGrados = {
    labels: getJsonScript("dataGradosLabels"),
    values: getJsonScript("dataGradosValues"),
  };

  const dataParalelos = {
    labels: getJsonScript("dataParalelosLabels"),
    values: getJsonScript("dataParalelosValues"),
  };

  const dataGestion = {
    labels: getJsonScript("dataGestionLabels"),
    values: getJsonScript("dataGestionValues"),
  };

  const totalHombres = Number(window.reportesConfig?.totalHombres || 0);
  const totalMujeres = Number(window.reportesConfig?.totalMujeres || 0);

  createDoughnutChart("chartNiveles", dataNiveles.labels, dataNiveles.values);
  createGenderChart("chartGenero", totalHombres, totalMujeres);
  createGradesChart("chartGrados", dataGrados.labels, dataGrados.values);
  createParalelosChart("chartParalelos", dataParalelos.labels, dataParalelos.values);
  createGestionChart("chartGestion", dataGestion.labels, dataGestion.values);
}


function createDoughnutChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);

  if (!ctx) return;

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: REPORT_COLORS.slice(0, labels.length),
          borderWidth: 0,
        },
      ],
    },
    options: getBaseChartOptions(true),
  });
}


function createGenderChart(canvasId, totalHombres, totalMujeres) {
  const ctx = document.getElementById(canvasId);

  if (!ctx) return;

  new Chart(ctx, {
    type: "pie",
    data: {
      labels: ["Masculino", "Femenino"],
      datasets: [
        {
          data: [totalHombres, totalMujeres],
          backgroundColor: ["#2563eb", "#ec4899"],
          borderWidth: 0,
        },
      ],
    },
    options: getBaseChartOptions(true),
  });
}


function createGradesChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);

  if (!ctx) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Estudiantes",
          data: data,
          backgroundColor: "#2563eb",
          borderRadius: 6,
        },
      ],
    },
    options: getBarChartOptions(false),
  });
}


function createParalelosChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);

  if (!ctx) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Estudiantes",
          data: data,
          backgroundColor: REPORT_COLORS.slice(6, 13),
          borderRadius: 4,
        },
      ],
    },
    options: getBarChartOptions(true),
  });
}


function createGestionChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);

  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Inscripciones",
          data: data,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          fill: true,
          tension: 0.3,
          pointBackgroundColor: "#2563eb",
          pointRadius: 5,
        },
      ],
    },
    options: getLineChartOptions(),
  });
}


function getBaseChartOptions(showLegend) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: showLegend,
        position: "bottom",
        labels: {
          padding: 16,
          font: {
            size: 12,
          },
        },
      },
    },
  };
}


function getBarChartOptions(horizontal = false) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? "y" : "x",
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          font: {
            size: horizontal ? 9 : 10,
          },
        },
      },
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
          font: {
            size: horizontal ? 9 : 10,
          },
        },
      },
    },
  };
}


function getLineChartOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          stepSize: 1,
        },
      },
    },
  };
}


function initReportAnimations() {
  const items = document.querySelectorAll(".reports-header, .reports-tabs, .reports-content");

  items.forEach((item, index) => {
    item.style.animationDelay = `${Math.min(index * 60, 220)}ms`;
    item.classList.add("report-fade-in");
  });
}

function initCourseExpand() {
  var panel = document.getElementById("course-students-panel");
  var panelTitle = document.getElementById("panel-course-title");
  var panelTbody = document.getElementById("panel-students-tbody");
  var panelTotal = document.getElementById("panel-total-count");
  var closeBtn = document.getElementById("panelCloseBtn");
  var printBtn = document.getElementById("panelPrintBtn");

  if (!panel || !panelTitle || !panelTbody) return;

  document.addEventListener("click", function (event) {
    var btn = event.target.closest(".btn-view-students");

    if (!btn) return;

    var idx = btn.dataset.courseIdx;
    var courseName = btn.dataset.courseName;
    var data = window._cursosEstudiantes;

    if (!data || !data[idx]) return;

    var curso = data[idx];

    panelTitle.textContent = curso.grado + " \"" + curso.paralelo + "\" - " + curso.nivel;

    if (printBtn) {
      printBtn.href = "/reportes/imprimir-lista/?gestion=" + curso.gestion_id + "&nivel=" + encodeURIComponent(curso.nivel) + "&grado=" + encodeURIComponent(curso.grado) + "&paralelo=" + encodeURIComponent(curso.paralelo);
    }

    panelTbody.innerHTML = "";

    if (curso.estudiantes.length === 0) {
      var tr = document.createElement("tr");
      var td = document.createElement("td");
      td.setAttribute("colspan", "6");
      td.className = "panel-empty";
      td.innerHTML = '<i class="fa-solid fa-user-slash"></i><p>No hay estudiantes inscritos en este curso.</p>';
      tr.appendChild(td);
      panelTbody.appendChild(tr);
    } else {
      curso.estudiantes.forEach(function (est, i) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + (i + 1) + "</td>" +
          "<td>" + est.ci + "</td>" +
          "<td>" + est.nombres + "</td>" +
          "<td>" + est.genero + "</td>" +
          '<td><span class="doc-badge doc-' + est.estado_doc_cls + '">' + est.estado_doc + "</span></td>" +
          "<td>" + est.rude + "</td>";
        panelTbody.appendChild(tr);
      });
    }

    panelTotal.textContent = curso.estudiantes.length + " estudiante(s)";
    panel.classList.remove("hidden");

    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      panel.classList.add("hidden");
    });
  }
}


function initPrintButtons() {
  const buttons = document.querySelectorAll(".js-print-report");

  buttons.forEach((button) => {
    button.addEventListener("click", function () {
      window.print();
    });
  });
}