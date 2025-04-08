// styling: https://plotly.com/javascript/figure-labels/

const keys_analog = ['Zeit', 'RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung',
    'Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte',
    'Speicher 5 Boden', 'VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'];

const keys_digital = ['Heizung: Pumpe', 'Kessel: Ladepumpe', 'Kessel: Freigabe', 'Hz Mischer auf', 'Hz Mischer zu',
    'Kessel Mischer auf', 'Kessel Mischer zu', 'Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil', 'Heizung An'];

const keys_all = keys_analog.concat(keys_digital);

const graphs = {
    'Pufferspeicher': ['Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte', 'Speicher 5 Boden'],
    'Solar': ['Außentemperatur', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'],
    'Heizung': ['VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe'],
    'Wärmeerzeuger': ['RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung']
}

// Zuordnung der digitalen Keys zu den Gruppen
const digital_mapping = {
    'Pufferspeicher': [],
    'Solar': ['Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil'],
    'Heizung': ['Heizung: Pumpe', 'Hz Mischer auf', 'Hz Mischer zu'],
    'Wärmeerzeuger': ['Heizung An', 'Kessel: Ladepumpe', 'Kessel: Freigabe',
'Kessel Mischer auf', 'Kessel Mischer zu']
};

let date = new Date();
const tz_offset = date.getTimezoneOffset() * 60000;

function toDate(unixtimestamp) {
    ds = new Date(unixtimestamp * 1000 - tz_offset).toISOString();
    return ds
}

// Funktion zum Erzeugen des heutigen Datums im gewünschten Format
function getToday() {
    return new Date(date.getTime() - tz_offset).toISOString().split('T')[0];
}

// Funktion zum Extrahieren des Query-Parameters aus der URL
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// Überprüfen, ob der 'today'-Parameter vorhanden ist
let today = getQueryParam('datum') || getToday();
let period = getQueryParam('period') || 'day';
// id = 4 holt alles
let jsonUrl = "http://kleinsthof.de/uvr1611/analogChart.php?date=" + today + "&id=4&period=" + period;

// Setze das heutige Datum als Standardwert im Datepicker
document.getElementById('datepicker').value = today;

// Event-Listener für den Datepicker
document.getElementById('datepicker').addEventListener('change', function () {
    let selectedDate = this.value; // Hole das ausgewählte Datum
    if (selectedDate) {
        today = selectedDate; // Aktualisiere das Datum
        jsonUrl = "http://kleinsthof.de/uvr1611/analogChart.php?date=" + today + "&id=4&period=" + period;

        // Daten neu laden und Diagramme aktualisieren
        fetch(jsonUrl)
            .then(response => response.json())
            .then(data => {
                let df = {};
                for (let i = 0; i < (data[0].length); i++) {
                    df[keys_all[i]] = [];
                }
                for (let i = 0; i < data.length; i++) {
                    row = data[i];
                    for (let k = 0; k < (row.length); k++) {
                        if (k === 0) {
                            df[keys_all[k]].push(toDate(row[k]));
                        } else {
                            df[keys_all[k]].push(row[k]);
                        }
                    }
                }
                processCharts(df); // Diagramme neu erstellen
            })
            .catch(error => console.error("Error fetching data:", error));
    }
});


fetch(jsonUrl)
  .then(response => response.json())
  .then(data => {
    // Process data
        let df = {};

        for (let i = 0; i < (data[0].length); i++) {
            df[keys_all[i]] = [];
        }

        for (let i = 0; i < data.length; i++) {
            row = data[i];
            for (let k = 0; k < (row.length); k++) {
                if (k === 0) {
                    df[keys_all[k]].push(toDate(row[k]));
                } else {
                    df[keys_all[k]].push(row[k]);
                }
            }
        }
    processCharts(df);
  })
  .catch(error => console.error("Error fetching data:", error));


// Funktion zum Erstellen der Diagramme
function processCharts(df) {
    let divs = [];

    // Für jede Gruppe ein kombiniertes Diagramm erstellen
    for (const [key, value] of Object.entries(graphs)) {
        let analog_traces = [];
        let digital_traces = [];

        // Analoge Spuren
        value.forEach(function (entry) {
            if (entry !== 'Zeit') {
                let trace = {
                    type: "scatter",
                    mode: "lines",
                    name: entry,
                    x: df['Zeit'],
                    y: df[entry],
                    xaxis: 'x',  // Gemeinsame X-Achse
                    yaxis: 'y'   // Obere Y-Achse
                };
                analog_traces.push(trace);
            }
        });

        // Digitale Spuren (nur die zur Gruppe passenden)
        const digital_keys = digital_mapping[key] || [];
        digital_keys.forEach(function (entry, index) {
            let trace = {
                type: "scatter",
                mode: "lines",
                line: { shape: 'hv' },  // Treppenform für digitale Werte
                fill: 'tozeroy',
                name: entry,
                x: df['Zeit'],
                y: df[entry],
                xaxis: 'x',          // Gemeinsame X-Achse
                yaxis: `y${index + 2}` // Separate Y-Achsen für digitale Werte
            };
            digital_traces.push(trace);
        });

        // Layout für Subplots
        let layout = {
            font: { color: '#dfdfdf' },
            title: {
                text: key,
                font: { color: "#ccc" }
            },
            showlegend: true,
            plot_bgcolor: "#000",
            paper_bgcolor: "#000",
            grid: {
                rows: 2,              // 2 Reihen: analog oben, digital unten
                columns: 1,
                pattern: 'independent',
                roworder: 'top to bottom'
            },
            xaxis: {              // Gemeinsame X-Achse
                gridcolor: "#333",
                gridwidth: 1
            },
            yaxis: {              // Analoge Y-Achse (oben)
                gridcolor: "#444",
                gridwidth: 1,
                zerolinecolor: "lightgreen",
                zerolinewidth: 1,
                domain: [0.25, 1] // 75% der Höhe für analog (0.75 von 1)
            }
        };

        // Dynamische Y-Achsen für digitale Werte (20% der analogen Höhe)
        const analog_height = 0.75; // Höhe des analogen Bereichs
        const digital_total_height = analog_height * 0.2; // 20% der analogen Höhe
        const digital_single_height = digital_total_height / digital_keys.length; // Höhe pro digitaler Spur

        digital_keys.forEach((_, index) => {
            layout[`yaxis${index + 2}`] = {
                showgrid: false,
                showticklabels: false,
                domain: [
                    index * digital_single_height, // Startpunkt
                    (index + 1) * digital_single_height // Endpunkt
                ]
            };
        });

        // Plot erstellen
        Plotly.newPlot(key, [...analog_traces, ...digital_traces], layout);
        divs.push(document.getElementById(key));
    }

    // Synchronisation der X-Achsen
    function relayout(ed, divs) {
        if (Object.entries(ed).length === 0) {
            return;
        }
        divs.forEach((div) => {
            let x = div.layout.xaxis;
            if (ed["xaxis.autorange"] && x.autorange) return;
            if (x.range[0] !== ed["xaxis.range[0]"] || x.range[1] !== ed["xaxis.range[1]"]) {
                let update = {
                    'xaxis.range[0]': ed["xaxis.range[0]"],
                    'xaxis.range[1]': ed["xaxis.range[1]"],
                    'xaxis.autorange': ed["xaxis.autorange"],
                };
                Plotly.relayout(div, update);
            }
        });
    }

    divs.forEach(div => {
        div.on("plotly_relayout", function (ed) {
            relayout(ed, divs);
        });
    });
}
