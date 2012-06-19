// Load the Visualization API and the piechart package.
google.load('visualization', '1.0', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.setOnLoadCallback(drawCharts);

function drawCharts() {
  drawChart(raw_graph_data_3tau, document.getElementById('graph_3tau'));
  drawChart(raw_graph_data_6tau, document.getElementById('graph_6tau'));
  drawChart(raw_graph_data_g3tau, document.getElementById('graph_g3tau'));
  drawChart(raw_graph_data_i3tau, document.getElementById('graph_i3tau'));
  drawChart(raw_graph_data_e3tau, document.getElementById('graph_e3tau'));
}

function drawChart(raw_data, element) {
  var data = new google.visualization.DataTable();
  data.addColumn('datetime', 'Date');
  data.addColumn({
    type: 'number',
    label: 'Time',
  });
  for (i in raw_data) {
    row_data = raw_data[i];
    var elapsed_seconds = row_data[1];
    var elapsed_minutes = Math.floor(elapsed_seconds / 60);
    elapsed_seconds -= elapsed_minutes * 60;
    date = new Date();
    date.setTime(row_data[0] * 1000);
    data.addRow([date, {v: row_data[1], f: elapsed_minutes + ":" + (elapsed_seconds < 10 ? "0" : "") + (Math.round(elapsed_seconds * 100) / 100)}]);
  }
  var options = {
    //title: '3 Tau scores over time'
    legend: {position: 'none'},
    pointSize: 4
  };
  var chart = new google.visualization.ScatterChart(element);
  chart.draw(data, options);
}
