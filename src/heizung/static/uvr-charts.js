// styling: https://plotly.com/javascript/figure-labels/

const keys_analog = [
    'Zeit', 'RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur',
    'Speicherladeleitung', 'Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf',
    'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte', 'Speicher 5 Boden',
    'VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe', 'Solarstrahlung',
    'VL Solar', 'Drehzahl Ladepumpe Solar'
];

const keys_digital = [
    'Heizung: Pumpe', 'Kessel: Ladepumpe', 'Kessel: Freigabe',
    'Hz Mischer auf', 'Hz Mischer zu', 'Kessel Mischer auf', 'Kessel Mischer zu',
    'Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil', 'Heizung An'
];

const keys_all = keys_analog.concat(keys_digital);

const graphs = {
    'Pufferspeicher': ['Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben',
                       'Speicher 3 Unten', 'Speicher 4 Mitte', 'Speicher 5 Boden'],
    'Solar':          ['Außentemperatur', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'],
    'Heizung':        ['VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe'],
    'Wärmeerzeuger':  ['RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur',
                       'Speicherladeleitung']
};

const digital_mapping = {
    'Pufferspeicher': [],
    'Solar':          ['Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil'],
    'Heizung':        ['Heizung: Pumpe', 'Hz Mischer auf', 'Hz Mischer zu'],
    'Wärmeerzeuger':  ['Heizung An', 'Kessel: Ladepumpe', 'Kessel: Freigabe',
                       'Kessel Mischer auf', 'Kessel Mischer zu']
};

// ── URL helpers ───────────────────────────────────────────────────────────────

function getQueryParam(param) {
    return new URLSearchParams(window.location.search).get(param);
}

function getToday() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000)
        .toISOString().split('T')[0];
}

function toDate(unixtimestamp) {
    const now = new Date();
    return new Date(unixtimestamp * 1000 - now.getTimezoneOffset() * 60000).toISOString();
}

// ── State ─────────────────────────────────────────────────────────────────────

let today  = getQueryParam('datum')  || getToday();
let period = getQueryParam('period') || 'day';

// ── Init UI ───────────────────────────────────────────────────────────────────

const datepicker = document.getElementById('datepicker');
datepicker.value = today;

function updateLinks() {
    document.getElementById('link-day').href  = `?datum=${today}&period=day`;
    document.getElementById('link-week').href = `?datum=${today}&period=week`;
    document.getElementById('link-day').className  = period === 'day'  ? 'active' : '';
    document.getElementById('link-week').className = period === 'week' ? 'active' : '';
}
updateLinks();

// ── Data loading ──────────────────────────────────────────────────────────────

function buildUrl() {
    return `/analogChart.php?date=${today}&id=4&period=${period}`;
}

function parseData(data) {
    const df = {};
    for (let i = 0; i < data[0].length; i++) df[keys_all[i]] = [];
    for (const row of data) {
        for (let k = 0; k < row.length; k++) {
            df[keys_all[k]].push(k === 0 ? toDate(row[k]) : row[k]);
        }
    }
    return df;
}

function loadAndRender() {
    fetch(buildUrl())
        .then(r => r.json())
        .then(data => processCharts(parseData(data)))
        .catch(err => console.error('Error fetching data:', err));
}

datepicker.addEventListener('change', function () {
    if (!this.value) return;
    today = this.value;
    window.history.pushState({}, '', `?datum=${today}&period=${period}`);
    updateLinks();
    loadAndRender();
});

loadAndRender();

// ── Settings modal (operating mode) ──────────────────────────────────────────

const overlay    = document.getElementById('modal-overlay');
const modeSelect = document.getElementById('mode-select');
const modalMsg   = document.getElementById('modal-msg');

function openModal() {
    modalMsg.textContent = '';
    modalMsg.className   = '';

    fetch('/settings/operating-mode')
        .then(r => r.json())
        .then(d => { modeSelect.value = d.operating_mode || 'pellets'; })
        .catch(() => { modalMsg.textContent = 'Modus konnte nicht geladen werden.'; modalMsg.className = 'err'; });

    overlay.classList.add('open');
}

function closeModal() { overlay.classList.remove('open'); }

document.getElementById('settings-btn').addEventListener('click', openModal);
document.getElementById('modal-cancel').addEventListener('click', closeModal);
overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });

document.getElementById('modal-save').addEventListener('click', () => {
    const mode = modeSelect.value;

    fetch(`/settings/operating-mode?mode=${mode}`, { method: 'PUT' })
        .then(r => {
            if (r.ok) {
                modalMsg.textContent = `Modus auf „${mode}" gesetzt.`;
                modalMsg.className   = 'ok';
                setTimeout(closeModal, 1200);
            } else if (r.status === 403) {
                modalMsg.textContent = 'Nur im lokalen Netzwerk (192.168.1.0/24) verfügbar.';
                modalMsg.className   = 'err';
            } else {
                modalMsg.textContent = `Fehler: ${r.status}`;
                modalMsg.className   = 'err';
            }
        })
        .catch(() => { modalMsg.textContent = 'Verbindungsfehler.'; modalMsg.className = 'err'; });
});

function processCharts(df) {
    const divs = [];

    for (const [key, analogKeys] of Object.entries(graphs)) {
        const analog_traces = analogKeys
            .filter(e => e !== 'Zeit')
            .map(e => ({
                type: 'scatter', mode: 'lines', name: e,
                x: df['Zeit'], y: df[e], xaxis: 'x', yaxis: 'y'
            }));

        const digital_keys = digital_mapping[key] || [];
        const digital_traces = digital_keys.map((e, i) => ({
            type: 'scatter', mode: 'lines', name: e,
            line: { shape: 'hv' }, fill: 'tozeroy',
            x: df['Zeit'], y: df[e], xaxis: 'x', yaxis: `y${i + 2}`
        }));

        const ANALOG_DOMAIN_START = 0.25;
        const DIGITAL_HEIGHT = (1 - ANALOG_DOMAIN_START) * 0.2 / Math.max(digital_keys.length, 1);

        const layout = {
            font:         { color: '#dfdfdf' },
            title:        { text: key, font: { color: '#ccc' } },
            showlegend:   true,
            plot_bgcolor:  '#000',
            paper_bgcolor: '#000',
            grid: { rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' },
            xaxis: { gridcolor: '#333', gridwidth: 1 },
            yaxis: {
                gridcolor: '#444', gridwidth: 1,
                zerolinecolor: 'lightgreen', zerolinewidth: 1,
                domain: [ANALOG_DOMAIN_START, 1],
                side: 'right'
            }
        };

        digital_keys.forEach((_, i) => {
            layout[`yaxis${i + 2}`] = {
                showgrid: false, showticklabels: false,
                domain: [i * DIGITAL_HEIGHT, (i + 1) * DIGITAL_HEIGHT]
            };
        });

        Plotly.newPlot(key, [...analog_traces, ...digital_traces], layout);
        divs.push(document.getElementById(key));
    }

    // Synchronise x-axis panning/zooming across all charts
    divs.forEach(div => {
        div.on('plotly_relayout', ed => {
            if (!Object.keys(ed).length) return;
            divs.forEach(other => {
                if (other === div) return;
                const x = other.layout.xaxis;
                if (ed['xaxis.autorange'] && x.autorange) return;
                if (x.range[0] !== ed['xaxis.range[0]'] || x.range[1] !== ed['xaxis.range[1]']) {
                    Plotly.relayout(other, {
                        'xaxis.range[0]':   ed['xaxis.range[0]'],
                        'xaxis.range[1]':   ed['xaxis.range[1]'],
                        'xaxis.autorange':  ed['xaxis.autorange']
                    });
                }
            });
        });
    });
}
