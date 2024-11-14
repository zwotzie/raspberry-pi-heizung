// styling: https://plotly.com/javascript/figure-labels/

keys_analog = ['Zeit', 'RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung',
    'Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte',
    'Speicher 5 Boden', 'VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'];

keys_digital = ['Heizung: Pumpe', 'Kessel: Ladepumpe', 'Kessel: Freigabe', 'Hz Mischer auf', 'Hz Mischer zu',
    'Kessel Mischer auf', 'Kessel Mischer zu', 'Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil', 'Heizung An'];

keys_all = keys_analog.concat(keys_digital);
graphs = {
    'Pufferspeicher': ['Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte', 'Speicher 5 Boden'],
    'Solar': ['Außentemperatur', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'],
    'Heizung': ['VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe'],
    'Wärmeerzeuger': ['RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung']
}

function toDate(unixtimestamp) {
    ds = new Date(unixtimestamp * 1000 - tz_offset).toISOString();
    return ds
}

var date = new Date();
const tz_offset = date.getTimezoneOffset() * 60000;
const today = toDate(date.getTime() / 1000).split('T')[0]

// id = 4 holt alles
var jsonUrl = "http://kleinsthof.de/uvr1611/analogChart.php?date=" + today + "&id=4&period=day";
Plotly.d3.json(jsonUrl, function (err, data) {
    //data = JSON.parse(data_json_str);
    /*
    console.log("data_json (string)" + data_json_str);
    console.log("data: " + data);
    console.log("data.length: " + data.length);
    */

    df = {};

    for (var i = 0; i < (data[0].length); i++) {
        df[keys_all[i]] = [];
    }


    for (var i = 0; i < data.length; i++) {
        row = data[i];
        for (var k = 0; k < (row.length); k++) {
            if (k == 0) {
                df[keys_all[k]].push(toDate(row[k]));
            } else {
                df[keys_all[k]].push(row[k]);
            }
        }
    }
    // Analog graphs
    for (const [key, value] of Object.entries(graphs)) {
        plot = []

        value.forEach(function (entry) {
            if (entry != 'Zeit') {
                add = {
                    type: "scatter",
                    mode: "lines",
                    name: entry,
                    x: df['Zeit'],
                    y: df[entry]
                }
                plot.push(add);
            }
        });

        var layout = {
            font: {color: '#dfdfdf'},
            title: {
                text: key,
                font: {color: "#ccc"}
            },
            showlegend: true,
            plot_bgcolor: "#000",
            paper_bgcolor: "#000",
            yaxis: {
                gridcolor: "#444",
                gridwidth: 1,
                zerolinecolor: "lightgreen",
                zerolinewidth: 1,
            },
            xaxis: {
                gridcolor: "#333",
                gridwidth: 1,
            },
            hoverlabel: {namelength: -1},
        };

        Plotly.newPlot(key, plot, layout);
    }

// digital graph
    traces = [];
    k = 0;
    keys_digital.forEach(function (entry) {
        // if (entry != 'Zeit') {
        k = k + 1;
        trace = {
            name: entry,
            mode: 'lines',
            line: {shape: 'hv'},
            type: 'scatter',
            fill: 'tozeroy',
            x: df['Zeit'],
            y: df[entry],
            // xaxis: `x${k}`,
            yaxis: `y${k}`,
        }
        // console.log(trace);
        traces.push(trace);
    });


    var layout_d = {
        font: {color: '#dfdfdf'},
        title: {
            text: "Digitale Werte",
            font: {size: 18, color: "#ccc"}
        },
        plot_bgcolor: "#000",
        paper_bgcolor: "#000",

        yaxis1: {showgrid: false, showticklabels: false},
        yaxis2: {showgrid: false, showticklabels: false},
        yaxis3: {showgrid: false, showticklabels: false},
        yaxis4: {showgrid: false, showticklabels: false},
        yaxis5: {showgrid: false, showticklabels: false},
        yaxis6: {showgrid: false, showticklabels: false},
        yaxis7: {showgrid: false, showticklabels: false},
        yaxis8: {showgrid: false, showticklabels: false},
        yaxis9: {showgrid: false, showticklabels: false},
        yaxis10: {showgrid: false, showticklabels: false},
        yaxis11: {showgrid: false, showticklabels: false},
        grid: {
            rows: traces.length,
            columns: 1,
            pattern: 'coupled',
            roworder: 'bottom to top',
        },
        hoverlabel: {namelength: -1},
    };

    Plotly.newPlot('digitals', traces, layout_d);

    var div1 = document.getElementById("Pufferspeicher");
    var div2 = document.getElementById("Solar");
    var div3 = document.getElementById("Heizung");
    var div4 = document.getElementById("Wärmeerzeuger");
    var div5 = document.getElementById("digitals");

    var divs = [div1, div2, div3, div4, div5];

    function relayout(ed, divs) {
        if (Object.entries(ed).length === 0) {
            return;
        }
        divs.forEach((div, i) => {
            let x = div.layout.xaxis;
            if (ed["xaxis.autorange"] && x.autorange) return;
            if (x.range[0] != ed["xaxis.range[0]"] || x.range[1] != ed["xaxis.range[1]"]) {
                var update = {
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

});