$(function() {
  $(".new_game_form").submit(function(e) {
    var params = [
      { 'name' : 'training', 'value' : $("#training").is(':checked') },
      { 'name' : 'classic_cards', 'value' : $("#classic_cards").is(':checked') },
      { 'name' : 'colour_blind', 'value' : $("#colour_blind").is(':checked') }
    ];

    var that = $(this);
    $.each(params, function(i, param) {
        var input = $('<input/>').attr('type', 'hidden')
            .attr('name', param.name)
            .attr('value', param.value);
        that.append(input);
    });
    
    return true;
  });
});

$(function() {
  var start = (("" + window.location).indexOf("https") == 0) ? "wss" : "ws";
  console.log("Using " + start);
  // Reconnect tuning.
  var RECONNECT_MIN_DELAY = 1000;
  var RECONNECT_MAX_DELAY = 30000;
  // A socket that stayed open at least this long counts as a healthy
  // connection, so the next drop starts retrying quickly again. A socket that
  // closes immediately keeps backing off instead of spinning.
  var STABLE_CONNECTION = 5000;

  // A dropped connection is usually momentary, so the first few retries go out
  // straight away rather than waiting for a backoff that is almost always
  // longer than the outage itself.
  var IMMEDIATE_RECONNECTS = 3;

  var ws = null;
  var reconnect_delay = RECONNECT_MIN_DELAY;
  var reconnect_timer = null;
  var reconnect_attempts = 0;
  var connected_at = 0;

  function connect() {
    if (reconnect_timer !== null) {
      clearTimeout(reconnect_timer);
      reconnect_timer = null;
    }
    if (ws) {
      // Detach the old socket first. Without this its onclose fires later and
      // schedules a second reconnect, leaving two sockets open at once.
      ws.onopen = null;
      ws.onmessage = null;
      ws.onclose = null;
      try { ws.close(); } catch (e) {}
    }
    ws = new WebSocket(start + "://" + window.location.host + "/gamelistwebsocket/" + see_more_ended);
    ws.onopen = on_ws_open;
    ws.onmessage = on_ws_message;
    ws.onclose = on_ws_close;
  }

  function reset_reconnect_backoff() {
    reconnect_attempts = 0;
    reconnect_delay = RECONNECT_MIN_DELAY;
  }

  function schedule_reconnect() {
    if (reconnect_timer !== null) {
      return;
    }
    var delay = 0;
    if (reconnect_attempts >= IMMEDIATE_RECONNECTS) {
      // Jitter stops every client retrying in lockstep after a server restart.
      delay = reconnect_delay + Math.floor(Math.random() * 500);
      reconnect_delay = Math.min(reconnect_delay * 2, RECONNECT_MAX_DELAY);
    }
    reconnect_attempts++;
    reconnect_timer = setTimeout(connect, delay);
  }

  // Coming back to a page that was hidden, or restoring it from the back
  // forward cache, should reconnect at once rather than sitting out whatever
  // backoff had built up while nobody was looking.
  function reconnect_now_if_down() {
    if (ws && (ws.readyState === WebSocket.OPEN ||
               ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    reset_reconnect_backoff();
    connect();
  }

  $(document).on("visibilitychange", function() {
    if (!document.hidden) {
      reconnect_now_if_down();
    }
  });
  $(window).on("pageshow", reconnect_now_if_down);

  // Anything sent while the socket is down (or still opening) is dropped
  // rather than throwing. Reconnecting re-requests the full state, so the only
  // thing lost is the action itself.
  function send(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  function on_ws_close() {
    if (connected_at && new Date().getTime() - connected_at >= STABLE_CONNECTION) {
      // The connection was healthy, so this is a fresh outage: allow immediate
      // retries again. A socket that closes straight after opening keeps its
      // backoff instead, so a game that no longer exists does not spin.
      reset_reconnect_backoff();
    }
    connected_at = 0;
    show_disconnected();
    schedule_reconnect();
  }

  function show_disconnected() {
    if (!$("#disconnected").length) {
      $("<div id=\"disconnected\">Connection lost \u2014 reconnecting\u2026 " +
        "<a href=\"javascript:location.reload(true)\">refresh now</a></div>")
          .prependTo("body");
    }
  }

  function hide_disconnected() {
    $("#disconnected").remove();
  }

  function on_ws_open() {
    connected_at = new Date().getTime();
    hide_disconnected();
    send({'type' : 'update'});
  }

  connect();

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
        } else if (game_data.type == "i93tau") {
          game_type = "Insane 9 3 Tau";
        } else if (game_data.type == "m3tau") {
          game_type = "Master 3 Tau";
        } else if (game_data.type == "e3tau") {
          game_type = "Easy 3 Tau";
        } else if (game_data.type == "4tau") {
          game_type = "Generalized 4 Tau";
        } else if (game_data.type == "r4tau") {
          game_type = "4 Tau";
        } else if (game_data.type == "3ptau") {
          game_type = "3 Projective Tau";
        } else if (game_data.type == "z3tau") {
          game_type = "Puzzle 3 Tau";
        } else if (game_data.type == "4otau") {
          game_type = "4 Outer Tau";
        } else if (game_data.type == "n3tau") {
          game_type = "Near 3 Tau";
        } else if (game_data.type == "bqtau") {
          game_type = "Boolean Quadruple Tau";
        } else if (game_data.type == "sbqtau") {
          game_type = "Small Boolean Quadruple Tau";
        }
        
        section.find(".games_list").append($("<li><a href=\"/game/" + game_data.id + "\">Game " + game_data.id + "</a> (" + game_type + ") " + (game_data.training ? "(Training) " : "") + "- " + players_string + "</li>"));
      }
      section.show();
    } else {
      section.hide();
    }
  }

  function on_ws_message(e) {
    var data = JSON.parse(e.data);
    if (data.type == "players") {
      // TODO: Show players in lobby.
    } else if (data.type == "games") {
      add_games($("#newgames"), data.new_games);
      add_games($("#startedgames"), data.started_games);
      add_games($("#endedgames"), data.ended_games);
    }
  }
});
