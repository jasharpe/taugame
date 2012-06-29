$(function(){
	$.extend($.fn.disableTextSelect = function() {
		return this.each(function(){
			if($.browser.mozilla){//Firefox
				$(this).css('MozUserSelect','none');
			}else if($.browser.msie){//IE
				$(this).bind('selectstart',function(){return false;});
			}else{//Opera, etc.
				$(this).mousedown(function(){return false;});
			}
		});
	});
});

$(document).ready(function() {
  var key_map = {
    'q' : 0,
    'a' : 1,
    'z' : 2,
    'w' : 3,
    's' : 4,
    'x' : 5,
    'e' : 6,
    'd' : 7,
    'c' : 8,
    'r' : 9,
    'f' : 10,
    'v' : 11,
    't' : 12,
    'g' : 13,
    'b' : 14,
    'y' : 15,
    'h' : 16,
    'n' : 17,
    'u' : 18,
    'j' : 19,
    'm' : 20
  };

  $(document).keypress(function(e) {
    var key = String.fromCharCode(e.charCode).toLowerCase();
    if (!in_chat_box && key_map.hasOwnProperty(key)) {
      select_card(parseInt(key_map[key]));
    }
    if (!in_chat_box && key === "p") {
      $("#chat_box").focus();
      return false;
    }
    if (key === "l") {
      pause(game_paused ? "unpause" : "pause");
      return false;
    }
  });

  // onfocus from chat box on escape. Helps with button mashing.
  $(document).keyup(function(e) {
    if (in_chat_box && e.keyCode === 27) {
      $("#chat_box").blur();
    }
  });

  $(window).focus(function() {
    $("body").focus();
  });

  $("#start").click(function() {
    ws.send(JSON.stringify({'type' : 'start'}));
  });

  var start = (("" + window.location).indexOf("https") == 0) ? "wss" : "ws";
  console.log("Using " + start);
  var ws = new WebSocket(start + "://" + window.location.host + "/websocket/" + game_id);
  ws.onopen = function() {
    ws.send(JSON.stringify({
        'type' : 'update'
    }));
  };

  function submit_tau(cards) {
    ws.send(JSON.stringify({
        'type' : 'submit',
        'cards' : cards
    }));
  };

  function pause(pause_or_unpause) {
    ws.send(JSON.stringify({
        'type' : 'pause',
        'pause' : pause_or_unpause,
    }));
  };

  function get_card_number(card) {
    return card[0] + 3 * card[1] + 9 * card[2] + 27 * card[3];
  };

  var in_chat_box = false;
  var current_time_updater = undefined;
  var card_index_to_div_map = {};
  var card_index_to_card_map = {};
  var last_server_time = 0;
  var last_server_time_browser_time = 0;

  var selection_model = {
    'selected' : []
  };

  function select_card(card_index) {
    if (!card_index_to_div_map.hasOwnProperty(card_index)) {
      return;
    }
    var model = selection_model['selected'];
    var card_div = card_index_to_div_map[card_index];
    index = model.indexOf(card_index);
    
    if (index == -1) {
      if (model.length == game_size) {
        select_card(model[game_size - 1]);
      }

      model.push(card_index);
      card_div.removeClass("unselectedCard");
      card_div.addClass("selectedCard");

      if (model.length == game_size) {
        var cards = [];
        for (var submit_index in model) {
          cards.push(card_index_to_card_map[model[submit_index]]);
        }
        submit_tau(cards);
      }
    } else {
      model.splice(index, 1);
      card_div.addClass("unselectedCard");
      card_div.removeClass("selectedCard");
    }
  };

  function update_scores(scores, ended) {
    score_list_table = $("#score_list");
    score_list_table.html('');
    var winner = undefined;
    var max_score = 0;
    if (ended) {
      for (var player in scores) {
        if (winner === undefined || scores[player].length > max_score) {
          winner = player;
          max_score = scores[player].length;
        }
      }
    }
    for (var player in scores) {
      var extra = "";
      if (ended && scores[player].length >= max_score) {
        extra = " (WINNER)";
      }
      score = $("<tr><td class=\"score_name\">" + player + extra + ":</td><td>" + scores[player].length + "</td></tr>");
      score_list_table.append(score);
    }
  };

  var prev_board = [];
  var card_to_board_map = {}
  var game_paused = false;
  function update_board(board, paused, target, number, hint, ended) {
    game_paused = paused;
    console.log("This board has " + number + " taus");

    var processed_hint = []
    if (hint !== null) {
      for (var card_index in hint) {
        processed_hint.push(get_card_number(hint[card_index]));
      }
    }

    var playing_area = $("#playing_area");
    old_selected = selection_model['selected'];
    selection_model['selected'] = [];
    playing_area.html('');

    if (paused) {
      var unpause_link = $("<a id=\"unpause\" tabindex=\"1\" href=\"javascript:void(0);\">Unpause</a>");
      unpause_link.click(function() {
        pause("unpause");
      });
      playing_area.append(unpause_link);
      return;
    }

    var table = $('<table style="display:inline-block;">');
    var max_row = 3;
    var max_col = board.length / max_row;
    card_index_to_div_map = {};
    card_index_to_card_map = {};
    var this_board = [];
    for (var row_index = 0; row_index < max_row; row_index++) {
      var row = $('<tr>');
      if (row_index === max_row - 1) {
        row.addClass("bottomRow");
      }
      for (var col_index = 0; col_index < max_col; col_index++) {
        var card_index = row_index + col_index * max_row;
        var card = board[card_index];
        var col = $('<td>');
        if (card === null) {
          var div = $('<div class="fakeCard">');
          col.append(div);
        } else {
          var div = $('<div class="realCard unselectedCard" data-card-index="' + card_index + '" data-card="' + card + '">');
          card_index_to_div_map[card_index] = div;
          card_index_to_card_map[card_index] = card;

          if (processed_hint.indexOf(get_card_number(card)) != -1) {
            div.addClass("hint");
          }

          prev_index = card_to_board_map[get_card_number(card)];
          if (prev_board.length > 0 && (prev_index === undefined || prev_index != card_index)) {
            div.css("background-color", "#FF8");
            div.animate({backgroundColor: "#FF8"}, 200)
               .animate({backgroundColor: "#FFF"}, 1000);
          }
          card_to_board_map[get_card_number(card)] = card_index;
          this_board.push(get_card_number(card));

          div.click(function(e) {
            select_card(parseInt($(this).attr("data-card-index")));
            return false;
          });

          var card_number = get_card_number(card);
          var offset = card_number * 80;

          div.css("background-position", "-" + offset + "px 0");
          col.append(div);
        }
        
        row.append(col);
        col.disableTextSelect();
      }
      if (target != null) {
        var col = $('<td>');
        var div = $('<div class="fakeCard">');
        col.append(div);
        row.append(col);
        if (row_index === 0 || row_index === 2) {
          row.append(col);
        } else {
          var card_div = $('<div class="realCard unselectedCard">');
          var card_number = get_card_number(target);
          var offset = card_number * 80;

          card_div.css("background-position", "-" + offset + "px 0");
          var col = $('<td>');
          col.append(card_div);
          row.append(col);
        }
      }
      table.append(row);
    }
    playing_area.append(table);
    prev_board = this_board;
  }

  function get_time(ended) {
    if (ended) {
      return Math.round(last_server_time);
    } else {
      return Math.round((last_server_time + (new Date().getTime() / 1000 - last_server_time_browser_time)))
    }
  };

  function format_time(seconds) {
    minutes = Math.floor(seconds / 60);
    seconds = seconds - minutes * 60;
    return minutes + (seconds < 10 ? ":0" : ":") + seconds;
  };

  function render_ranks(rank_element, player_rank_info) {
    function thing(rank_data) {
      rank_element.append("<div class=\"rank\">All players: <span title=\"" + rank_data.all.alltime.percentile + "%ile\">#" + rank_data.all.alltime.rank + "</span> <a href=\"/leaderboard/alltime\">all time</a>, <span title=\"" + rank_data.all.thisweek.percentile + "%ile\">#" + rank_data.all.thisweek.rank + "</span> <a href=\"/leaderboard/thisweek\">this week</a>, and <span title=\"" + rank_data.all.today.percentile + "%ile\">#" + rank_data.all.today.rank + "</span> <a href=\"/leaderboard/today\">today</a></div>");
      if (rank_data.personal !== null) {
        rank_element.append("<div class=\"rank\">Personal: <span title=\"" + rank_data.personal.alltime.percentile + "%ile\">#" + rank_data.personal.alltime.rank + "</span> <a href=\"/leaderboard/alltime/" + user_name + "\">all time</a>, <span title=\"" + rank_data.personal.thisweek.percentile + "%ile\">#" + rank_data.personal.thisweek.rank + "</span> <a href=\"/leaderboard/thisweek/" + user_name + "\">this week</a>, and <span title=\"" + rank_data.personal.today.percentile + "%ile\">#" + rank_data.personal.today.rank + "</span> <a href=\"/leaderboard/today/" + user_name + "\">today</a></div>");
      }
    }

    thing(player_rank_info.exact);
    rank_element.append("Within 5 seconds of:");
    thing(player_rank_info.close);
  };

  function update_time(time, paused, avg_number, ended, player_rank_info) {
    last_server_time = time;
    last_server_time_browser_time = new Date().getTime() / 1000;
    $("#time").html('');
    $("#rank").html('');
    var time_display = $("<span id=\"time_display\">");
    time_display.html(format_time(get_time(ended)));
    if (ended) {
      $("#time").append($("<span>TOTAL TIME: </span>"));
      if (player_rank_info !== null) {
        render_ranks($("#rank"), player_rank_info);
      }
    } else {
      $("#time").append($("<span>ELAPSED TIME: </span>"));
      clearInterval(current_time_updater);
      if (!paused) {
        current_time_updater = setInterval(function() {
          seconds = get_time(ended);
          time_display.html(format_time(seconds));
        }, 500);
      }
    }
    $("#time").append(time_display);
    if (avg_number !== null) {
      console.log(avg_number);
    }
  };

  function update(board, paused, target, scores, time, avg_number, number, ended, hint, player_rank_info) {
    update_scores(scores, ended);
    
    update_time(time, paused, avg_number, ended, player_rank_info);

    // update board
    update_board(board, paused, target, number, hint, ended);

    if (ended) {
      $("body").addClass("ended");
    }
  };

  function update_messages(text_area, name, message) {
    var is_at_bottom = text_area[0].scrollHeight - text_area.scrollTop() <= text_area.outerHeight();
    text_area.append($("<div class=\"message\"><span class=\"name\">" + name + ":</span> " + message + "</div>"));
    if (is_at_bottom) {
      text_area.scrollTop(text_area[0].scrollHeight - text_area.outerHeight() + 5);
    }
  }

  ws.onmessage = function (e) {
    var data = JSON.parse(e.data);
    if (data.type == "update") {
      update(data.board, data.paused, data.target, data.scores, data.time, data.avg_number, data.number, data.ended, data.hint, data.player_rank_info);
    } else if (data.type == "scores") {
      update_scores(data.scores, data.ended);
    } else if (data.type == "chat") {
      var text_area = $("#chat");
      update_messages($("#chat"), data.name, data.message);
    } else if (data.type == "history") {
      var text_area = $("#chat");
      text_area.html("");
      data.messages.forEach(function(chat_message) {
        update_messages(text_area, chat_message[0], chat_message[1]);
      });
      $("#chat_box").removeAttr("disabled");
      $("#say").removeAttr("disabled");
    }
  }

  ws.onclose = function() {
    $("body").prepend($("<span>DISCONNECTED - <a href=\"javascript:location.reload(true)\">REFRESH</a> (if you can't connect at all, <a href=\"" + window.location.href.replace("http:", "https:") + "\">try https</a> (ignore any warnings you see, my certificate is not good))</span>"));
    $("body").css("background-color", "red");
  };

  // CHAT

  function on_chat(e) {
    var chat_box = $("#chat_box");
    if (event.type == "click" || event.keyCode == '13') {
      ws.send(JSON.stringify({
        'type' : 'chat',
        'name' : user_name,
        'message' : chat_box.val()
      }));
      chat_box.val("");
    }
  };

  $("#chat_box").keypress(on_chat);
  $("#chat_box").focus(function (e) {
    in_chat_box = true;
  });
  $("#chat_box").blur(function (e) {
    in_chat_box = false;
  });
  $("#say").click(on_chat);
});
