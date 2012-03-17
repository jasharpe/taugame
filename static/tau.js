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
    var key = String.fromCharCode(e.keyCode);
    if (!in_chat_box && key_map.hasOwnProperty(key)) {
      select_card(parseInt(key_map[key]));
    }
  });

  $("#start").click(function() {
    ws.send(JSON.stringify({'type' : 'start'}));
  });

  var ws = new WebSocket("ws://" + window.location.host + "/websocket/" + game_id);
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

  var prev_board = []
  function update_board(board, hint) {
    var processed_hint = []
    if (hint !== null) {
      for (var card_index in hint) {
        processed_hint.push(get_card_number(hint[card_index]));
      }
    }

    var playing_area = $("#playing_area");
    selection_model['selected'] = [];
    playing_area.html('');
    var table = $('<table>');
    playing_area.append(table);
    var max_row = 3;
    var max_col = board.length / max_row;
    card_index_to_div_map = {};
    card_index_to_card_map = {};
    var this_board = [];
    for (var row_index = 0; row_index < max_row; row_index++) {
      var row = $('<tr>');
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

          if (prev_board.length > 0 && prev_board.indexOf(get_card_number(card)) == -1) {
            div.css("background-color", "#FF8");
            div
              .animate({backgroundColor: "#FF8"}, 200)
              .animate({backgroundColor: "#FFF"}, 1000);
          }
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
      table.append(row);
    }
    prev_board = this_board;
  }

  function update(board, scores, time, ended, hint) {
    update_scores(scores, ended);
    
    // update time
    last_server_time = time;
    last_server_time_browser_time = new Date().getTime() / 1000;
    $("#time").html('');
    var time_display = $("<span id=\"time_display\">");
    time_display.html((Math.round((last_server_time + (new Date().getTime() / 1000 - last_server_time_browser_time)))) + " seconds");
    if (ended) {
      $("#time").append($("<span>TOTAL TIME:</span>"));
    } else {
      $("#time").append($("<span>ELAPSED TIME:</span>"));
      clearInterval(current_time_updater);
      current_time_updater = setInterval(function() {
        time_display.html((Math.round((last_server_time + (new Date().getTime() / 1000 - last_server_time_browser_time)))) + " seconds");
      }, 500);
    }
    $("#time").append(time_display);

    // update board
    update_board(board, hint);

    if (ended) {
      $("body").addClass("ended");
    }
  };

  function update_messages(text_area, name, message) {
    var is_at_bottom = text_area[0].scrollHeight - text_area.scrollTop() <= text_area.outerHeight();
    text_area.append($("<div class=\"message\"><span class=\"name\">" + name + ":</span> " + message + "</div>"));
    if (is_at_bottom) {
      text_area.scrollTop(text_area[0].scrollHeight - text_area.outerHeight());
    }
  }

  ws.onmessage = function (e) {
    var data = JSON.parse(e.data);
    if (data.type == "update") {
      update(data.board, data.scores, data.time, data.ended, data.hint);
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
    $("body").prepend($("<span>DISCONNECTED - REFRESH</span>"));
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
