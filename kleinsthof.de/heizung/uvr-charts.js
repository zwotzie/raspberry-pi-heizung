keys_analog = ['Zeit', 'RL Kessel', 'Drehzahl Ladepumpe Kessel', 'Kessel Betriebstemperatur', 'Speicherladeleitung',
 'Außentemperatur', 'Raum RASPT', 'Speicher 1 Kopf', 'Speicher 2 Oben', 'Speicher 3 Unten', 'Speicher 4 Mitte',
 'Speicher 5 Boden', 'VL Heizung', 'RL Heizung', 'Drehzahl Heizungspumpe', 'Solarstrahlung', 'VL Solar', 'Drehzahl Ladepumpe Solar'];

keys_digital = ['Heizung: Pumpe', 'Kessel: Ladepumpe', 'Kessel: Freigabe', 'Hz Mischer auf', 'Hz Mischer zu',
 'Kessel Mischer auf', 'Kessel Mischer zu', 'Solarkreispumpe', 'Solar: Ladepumpe', 'Solar: Freigabeventil'];

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
const today = toDate(date.getTime()/1000).split('T')[0]

// id = 4 holt alles
var jsonUrl = "http://kleinsthof.de/uvr1611/analogChart.php?date=" + today + "&id=4&period=day";
Plotly.d3.json(jsonUrl, function(err, data) {
    //data = JSON.parse(data_json_str);
    /*
    console.log("data_json (string)" + data_json_str);
    console.log("data: " + data);
    console.log("data.length: " + data.length);
    */

    df = {};

    for (var i=0; i < (data[0].length); i++) {
            df[keys_all[i]] = [];
    }


    for (var i=0; i < data.length; i++) {
        row = data[i];
        for (var k=0; k < (row.length); k++) {
            if (k == 0) {
                df[keys_all[k]].push( toDate(row[k]) );
            }else{
                df[keys_all[k]].push( row[k] );
            }
        }
    }

    for (const [key, value] of Object.entries(graphs)) {
        plot=[]

        value.forEach(function(entry){
            if (entry != 'Zeit') {
                add = {  type: "scatter",
                    mode: "lines",
                    name: entry,
                    x: df['Zeit'],
                    y: df[entry]
                }
            plot.push(add);
            }
        });

        var layout = {
          title: key,
          showlegend: true,
        };

        Plotly.newPlot(key, plot, layout);
    }

    var div1 = document.getElementById("Pufferspeicher");
    var div2 = document.getElementById("Solar");
    var div3 = document.getElementById("Heizung");
    var div4 = document.getElementById("Wärmeerzeuger");

    var divs = [div1, div2, div3, div4];

    function relayout(ed, divs) {
      if (Object.entries(ed).length === 0) {return;}
      divs.forEach((div, i) => {
        let x = div.layout.xaxis;
        if (ed["xaxis.autorange"] && x.autorange) return;
        if (x.range[0] != ed["xaxis.range[0]"] ||x.range[1] != ed["xaxis.range[1]"])
        {
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
      div.on("plotly_relayout", function(ed) {relayout(ed, divs);});
    });

});