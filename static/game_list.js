$(function() {
  var start = (("" + window.location).indexOf("https") == 0) ? "wss" : "ws";
  console.log("Using " + start);
  var ws = new WebSocket(start + "://" + window.location.host + "/gamelistwebsocket/" + see_more_ended);

  ws.onopen = function() {
    ws.send(JSON.stringify({
        'type' : 'update'
    }));
  };

  function add_games(section, games) {
    section.find(".games_list").html('');
    if (games.length !== 0) {
      for (i in games) {
        var game_data = games[i];
        
        var players_string = "<span style=\"color:#ccc\">Empty</span>";
        if (game_data.players.length > 0) {
          players_string = game_data.players.join(", ");
        }

        var game_type = "Unknown game type";
        if (game_data.type === "3tau") {
          game_type = "3 Tau";
        } else if (game_data.type === "6tau") {
          game_type = "6 Tau";
        } else if (game_data.type === "g3tau") {
          game_type = "Generalized 3 Tau";
        } else if (game_data.type == "i3tau") {
          game_type = "Insane 3 Tau";
        }

        section.find(".games_list").append($("<li><a href=\"/game/" + game_data.id + "\">Game " + game_data.id + "</a> (" + game_type + ") - " + players_string + "</li>"));
      }
      section.show();
    } else {
      section.hide();
    }
  }

  ws.onmessage = function (e) {
    var data = JSON.parse(e.data);
    if (data.type == "players") {
      // TODO
    } else if (data.type == "games") {
      console.log(data);
      add_games($("#newgames"), data.new_games);
      add_games($("#startedgames"), data.started_games);
      add_games($("#endedgames"), data.ended_games);
    }
  };

  ws.onclose = function() {
    $("body").prepend($("<span>DISCONNECTED - <a href=\"javascript:location.reload(true)\">REFRESH</a> (if you can't connect at all, <a href=\"" + window.location.href.replace("http:", "https:") + "\">try https</a> (ignore any warnings you see, my certificate is not good))</span>"));
    $("body").css("background-color", "red");
  };
});
