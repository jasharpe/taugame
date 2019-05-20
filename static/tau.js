$(function(){
  // Hack to make iOS 6 work.
  if (navigator.userAgent.match(/iPhone OS 6_1_6/i) != null) {
    var css = document.createElement('link');
    css.type = "text/css";
    css.rel = "stylesheet";
    css.href = "/static/ios6.css";
    var h = document.getElementsByTagName('head')[0];
    h.appendChild(css);
  }

  $.extend($.fn.disableTextSelect = function() {
    return this.each(function() {
      if ($.browser.mozilla) {  // Firefox
        $(this).css('MozUserSelect','none');
      } else if ($.browser.msie){  // IE
        $(this).bind('selectstart', function() { return false; });
      } else {  // Opera, etc.
        $(this).mousedown(function(){return false;});
      }
    });
  });
});

function ready() {
  $("#waiting").text("ready");
}

function waiting() {
  if ($("#waiting").length === 0) {
    $("body").append($('<div id="waiting" style="display:none;">waiting</div>'));
  } else {
    $("#waiting").text("waiting");
  }
}

$(document).ready(function() {
  waiting();

  var properties = ['Colour', 'Number', 'Shading', 'Shape'];

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
    if (!in_chat_box && key === "l") {
      pause(game_paused ? "unpause" : "pause");
      return false;
    }
    if (!in_chat_box && key === "k") {
      var hint_button = $("#hint");
      if (hint_button && hint_button.is(":visible")) {
        hint_button.click();
      }
    }
    if (!in_chat_box && key === " ") {
      if ($("#start").length) {
        start();
      } else {
        deselect_all_cards();
      }
      return false;
    }
  });
  
  function start() {
    ws.send(JSON.stringify({'type' : 'start'}));
    waiting();
  }

  // onfocus from chat box on escape. Helps with button mashing.
  $(document).keyup(function(e) {
    if (in_chat_box && e.keyCode === 27) {
      $("#chat_box").blur();
    }
  });

  $(window).focus(function() {
    $("body").focus();
  });

  $("#start").click(start);

  var ws_type = (("" + window.location).indexOf("https") == 0) ? "wss" : "ws";
  console.log("Using " + ws_type);
  var ws = new WebSocket(ws_type + "://" + window.location.host + "/websocket/" + game_id);
  ws.onopen = function() {
    $("#connecting").hide();
    $("#start").show();
    ws.send(JSON.stringify({
        'type' : 'update'
    }));
  };

  function submit_tau(cards) {
    if (all_tau_strings[tau_to_string(cards)]) {
      ws.send(JSON.stringify({
          'type' : 'submit',
          'cards' : cards
      }));
      waiting()
      last_submit_time = new Date().getTime();
      for (i in cards) {
        var card_number = get_card_number(cards[i]);
        var div = card_number_to_div_map[card_number];
        div.stop();
        div.css("background-color", "#FFF");
        div.animate({backgroundColor: "#FFF"}, 100)
           .animate({backgroundColor: "#DFD"}, 400);
      }
      setTimeout(function() {
        deselect_all_cards();
      }, 100);
    } else if (all_stale_tau_strings[tau_to_string(cards)]) {
      if (game_type === "z3tau") {
        var index = stale_tau_to_index_map[tau_to_string(cards)];
        var found_puzzle_taus = $($(".found_puzzle_tau")[index]).find(".smallCard").each(function (index, raw_card) {
          var card  = $(raw_card);
          card.stop();
          card.css("background-color", "#FBB");
          card.animate({backgroundColor: "#FBB"}, 200)
              .animate({backgroundColor: "#FFF"}, 1000);
        });
        setTimeout(function() {
          deselect_all_cards();
        }, 100);
      }
    } else {
      for (i in cards) {
        var card_number = get_card_number(cards[i]);
        var div = card_number_to_div_map[card_number];
        div.stop();
        div.css("background-color", "#FEE");
        div.animate({backgroundColor: "#FEE"}, 200)
           .animate({backgroundColor: "#FFF"}, 500);
      }
    }
  };

  function pause(pause_or_unpause) {
    ws.send(JSON.stringify({
        'type' : 'pause',
        'pause' : pause_or_unpause,
    }));
  };

  function get_card_number(card) {
    if (game_type === "3ptau") {
      return card[0] + 4 * card[1] + 16 * card[2] - 1;
    } else if (game_type === "bqtau" || game_type === "sbqtau") {
      return card[0] + 4 * card[1] + 16 * card[2];
    } else {
      return card[0] + 3 * card[1] + 9 * card[2] + 27 * card[3];
    }
  };

  function tau_to_string(tau) {
    var card_numbers = [];
    for (var i in tau) {
      card_numbers.push(get_card_number(tau[i]));
    }
    card_numbers = card_numbers.sort();
    var tau_string = "";
    for (var i in card_numbers) {
      tau_string += card_numbers[i] + ","
    }
    return tau_string;
  }

  var last_submit_time = 0;
  var all_tau_strings = {};
  var all_stale_tau_strings = {};
  var game_ended = false;
  var in_chat_box = false;
  var current_time_updater = undefined;
  var card_number_to_div_map = {};
  var card_index_to_div_map = {};
  var card_index_to_card_map = {};
  var stale_tau_to_index_map = {};
  var last_server_time = 0;
  var last_server_time_browser_time = 0;
  var last_found_puzzle_taus = null;
  var last_hint_tau_string = "";
  var hints_given = 0;
  var hint_cards = [];
  var selection_model = {
    'selected' : []
  };

  function deselect_all_cards() {
    while (selection_model['selected'].length > 0) {
      select_card(selection_model['selected'][0]);
    }
  }

  function select_card(card_index, do_not_submit) {
    if (game_ended) {
      return;
    }
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
        if (do_not_submit !== true) {
          submit_tau(cards);
        }
      }
    } else {
      model.splice(index, 1);
      card_div.addClass("unselectedCard");
      card_div.removeClass("selectedCard");
    }
  };

  function update_scores(scores, ended, is_pausable) {
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

  function getImgClass() {
    var colour_blind = $.cookie("colour_blind") === "true";
    var classic_cards = $.cookie("classic_cards") === "true";
    var new_projective_cards = $.cookie("new_projective_cards") !== "false";
    var hanchul_222_projective_cards = $.cookie("hanchul_proj_222") === "true";
    var hanchul_33_projective_cards = $.cookie("hanchul_proj_33") === "true";
    var hanchul_quad_cards = $.cookie("hanchul_quad") === "true"
    if (game_type === "3ptau") {
      if (new_projective_cards) {
        return "projectiveTauNew";
      } else if (hanchul_222_projective_cards) {
        return "projectiveTauHanchul222";
      } else if (hanchul_33_projective_cards) {
        return "projectiveTauHanchul33";
      } else {
        return "projectiveTau";
      }
    } else if (game_type === "bqtau" || game_type === "sbqtau") {
      if (hanchul_quad_cards) {
        return "booleanTauHanchul";
      } else {
        return "booleanTau";
      }
    } else if (classic_cards && colour_blind) {
      return "colourBlindClassicTau";
    } else if (classic_cards) {
      return "classicTau";
    } else {
      return "regularTau";
    }
  }

  function getSmallImgClass() {
    var colour_blind = $.cookie("colour_blind") === "true";
    var classic_cards = $.cookie("classic_cards") === "true";
    if (classic_cards && colour_blind) {
      return "smallColourBlindClassicTau";
    } else if (classic_cards) {
      return "smallClassicTau";
    } else {
      return "smallRegularTau";
    }
  }

  var prev_board = [];
  var card_to_board_map = {}
  var game_paused = false;
  function update_board(board, paused, target, wrong_property, number, hint, ended, found_puzzle_taus, training_options) {
    var string = "";
    $.each(board, function(i, tau) {
      string += "[" + tau + "]";
    });
    console.log("Client says board is: " + string);
    console.log("This board has " + number + " taus");

    var processed_hint = []
    if (hint !== null) {
      for (var card_index in hint) {
        processed_hint.push(get_card_number(hint[card_index]));
      }
    }

    var playing_area = $("#playing_area");
    playing_area.html('');
    old_selected = selection_model['selected'];
    old_selected_card_numbers = [];
    for (var i in old_selected) {
      old_selected_card_numbers.push(get_card_number(card_index_to_card_map[old_selected[i]]));
    }
    selection_model['selected'] = [];

    if (paused) {
      var unpause_link = $("<a id=\"unpause\" tabindex=\"1\" href=\"javascript:void(0);\">Unpause</a>");
      unpause_link.click(function() {
        pause("unpause");
      });
      playing_area.append($('<span id="paused">Paused</span>'));
      return;
    }

    if (training && ["n3tau"].indexOf(game_type) !== -1) {
      var options = $('<div id="training_options">');
      if (game_type === "n3tau") {
        var property_select = $('<select id="property_picker" name="property"><option value="all">All</option><option value="shape">Shape</option><option value="shading">Shading</option><option value="number">Number</option><option value="colour">Colour</option></select>');
        if (training_options['property'] !== null) {
          property_select.val(training_options['property']);
        }
        property_select.change(function(e) {
          var selected = $('#property_picker option:selected');
          ws.send(JSON.stringify({
            'type' : 'training_option',
            'option' : 'property',
            'value' : selected.val()
          }));
        });
        options.append($('<label for="property">Property:</label>"'));
        options.append(property_select);
      }
      playing_area.append(options);
    }

    playing_area.append($('<div style="clear:both;"/>'));
    var table = $('<table id="playing_area_table" style="display:block; float:left;">');
    var max_row = 3;
    var max_col = board.length / max_row;
    var hints_printed = 0;
    card_number_to_div_map = {};
    card_index_to_div_map = {};
    card_index_to_card_map = {};
    hint_cards = []
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
          div.addClass(getImgClass());
          card_number_to_div_map[get_card_number(card)] = div;
          card_index_to_div_map[card_index] = div;
          card_index_to_card_map[card_index] = card;

          if (!training && processed_hint.indexOf(get_card_number(card)) != -1) {
            div.addClass("hint");
          } else if (training && processed_hint.indexOf(get_card_number(card)) != -1) {
            hint_cards.push(div);
            if (hints_printed < hints_given) {
              div.addClass("hint");
              hints_printed++;
            }
          }

          prev_index = card_to_board_map[get_card_number(card)];
          if (prev_board.length > 0 && (prev_index === undefined || prev_index != card_index)) {
            if ($.cookie("new_card_animation") !== "false") {
              div.css("background-color", "#FF8");
              div.animate({backgroundColor: "#FF8"}, 200)
                 .animate({backgroundColor: "#FFF"}, 1000);
            }
          }
          card_to_board_map[get_card_number(card)] = card_index;
          this_board.push(get_card_number(card));

          div.bind("touchstart click", function(e) {
            select_card(parseInt($(this).attr("data-card-index")));
            return false;
          });
          div.bind("touchend", function(e) {
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
          card_div.addClass(getImgClass());
          var card_number = get_card_number(target);
          var offset = card_number * 80;

          card_div.css("background-position", "-" + offset + "px 0");
          var col = $('<td>');
          col.append(card_div);
          row.append(col);
        }
      }
      if (wrong_property !== null) {
        var col = $('<td>');
        var div = $('<div class="fakeCard">');
        col.append(div);
        row.append(col);
        if (row_index === 0 || row_index === 2) {
          row.append(col);
        } else {
          var card_div = $('<div class="realCard unselectedCard">');
          card_div.addClass("nearTau");
          var offset = wrong_property * 80;
          card_div.css("background-position", "-" + offset + "px 0");
          var col = $('<td>');
          col.append(card_div);
          row.append(col);
        }
      }
      table.append(row);
    }
    playing_area.append(table);
    
    if (found_puzzle_taus != null) {
      var found_puzzle_taus_div = $("<div id=\"found_puzzle_taus\" style=\"float:left;\">");
      for (var i in found_puzzle_taus) {
        var tau_div = $('<div class="found_puzzle_tau">');
        for (var j in found_puzzle_taus[i]) {
          card = found_puzzle_taus[i][j];
          var card_number = get_card_number(card);
          var offset = card_number * 40;
          var card_div = $('<div class="smallCard ' + getSmallImgClass() + '">');
          card_div.css("background-position", "-" + offset + "px 0");
          tau_div.append(card_div);
          if (last_found_puzzle_taus !== null && i >= last_found_puzzle_taus.length) {
            card_div.css("background-color", "#FF8");
            card_div.animate({backgroundColor: "#FF8"}, 200)
                .animate({backgroundColor: "#FFF"}, 1000);
          }
        }
        found_puzzle_taus_div.append(tau_div);
      }
      playing_area.append(found_puzzle_taus_div);
      last_found_puzzle_taus = found_puzzle_taus;
    }
    
    playing_area.append($('<div style="clear:both;"/>'));

    prev_board = this_board;

    // Update selection with old selection.
    var selection_still_good = true;
    for (var i in old_selected) {
      if (!(old_selected[i] in card_index_to_card_map)) {
        selection_still_good = false;
        break;
      }
      selection_still_good = selection_still_good && old_selected_card_numbers[i] == get_card_number(card_index_to_card_map[old_selected[i]]);
    }

    if (selection_still_good) {
      for (var i in old_selected) {
        // In puzzle 3 tau, we may reselect an existing tau here. Force it to
        // not be submitted if this is the case, since it'll cause a red flash
        // not connected to an intended user submit.
        select_card(old_selected[i], true /* do_not_submit */);
      }
    }

    // Update zoom.
    document.getElementsByTagName('body')[0].style.zoom = 1;
    var num_cols = 0;
    $('#playing_area_table tr').each(function() {
      cand_cols = 0;
      $(this).find("td").each(function() {
        cand_cols++;
      });
      num_cols = Math.max(num_cols, cand_cols);
    });
    var game_width = num_cols * 90 + 4;
    var zoom = Math.min(1, screen.availWidth / game_width).toFixed(2);
    document.getElementsByTagName('body')[0].style.zoom = zoom;
  }

  function update_buttons(ended, paused, is_pausable) {
    var buttons_div = $("#buttons");
    buttons_div.html('');
    var pause_button = $('<button id="pause">Pause</button>');
    if (paused) {
      pause_button.text("Unpause");
    }
    if (ended || (!paused && !is_pausable)) {
      pause_button.attr('disabled', 'disabled');
    }
    pause_button.click(function() {
      pause(paused ? "unpause" : "pause");
    });
    buttons_div.append(pause_button);
    if (training) {
      var hint_button = $('<button id="hint">Hint</button>');
      hint_button.click(function() {
        hint_cards[hints_given].addClass("hint");
        hints_given++;
        if (hints_given >= game_size) {
          hint_button.attr("disabled", "disabled");
        }
      });
      if (ended || paused || hint_cards.length === 0 || hints_given >= game_size) {
        hint_button.attr("disabled", "disabled");
      }
      buttons_div.append(hint_button);
    }
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
    function thing2(label, rank_data, user_name) {
      rank_element.append("<div class=\"rank\">" + label + ": <span title=\"" + rank_data.alltime.percentile + "%ile\">#" + rank_data.alltime.rank + "</span> <a href=\"/leaderboard/alltime/" + user_name + "#" + game_type + "\">all time</a>, <span title=\"" + rank_data.thisweek.percentile + "%ile\">#" + rank_data.thisweek.rank + "</span> <a href=\"/leaderboard/thisweek/" + user_name + "#" + game_type + "\">this week</a>, and <span title=\"" + rank_data.today.percentile + "%ile\">#" + rank_data.today.rank + "</span> <a href=\"/leaderboard/today/" + user_name + "#" + game_type + "\">today</a></div>");
    }

    function thing(rank_data) {
      thing2("All players", rank_data.all, "");
      if (rank_data.personal !== null) {
        thing2("Personal", rank_data.personal, user_name)
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

  function update_new_game() {
    var div = $("#new_game");
    div.html('');
    var tab_index = 10;

    function add(elt, display, predicate) {
      for (var game_index = 0; game_index < game_type_info.length; game_index++) {
        var new_game_info = game_type_info[game_index];
        if (!predicate(new_game_info)) {
          continue;
        }
        var new_game_type = new_game_info[0];
        var game_type_string = new_game_info[1];
        var form = $('<form style="display:' + display + ';" name="new_game" action="/new_game/' + new_game_type + '?parent=' + game_id + '" method="post"><input type="submit" tabindex="' + tab_index + '" value="New ' + game_type_string + ' game" /></form>');
        form.submit(function(e) {
          var params = [
            { 'name' : 'training', 'value' : $("#training").is(':checked') },
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
        elt.append(form);
        tab_index++;
      }
    }
    add(div, 'inline-block', function(new_game_info) {
        return new_game_info[2] === "False" && new_game_info[3] === "False"
    });
    
    var variants = $('<details/>');
    variants.append($('<summary>Variants</summary>'));
    add(variants, 'block', function(new_game_info) {
        return new_game_info[2] === "True";
    });
    div.append(variants);

    var obscure_variants = $('<details/>');
    obscure_variants.append($('<summary>Obscure Variants</summary>'));
    add(obscure_variants, 'block', function(new_game_info) {
        return new_game_info[3] === "True";
    });
    div.append(obscure_variants);

    div.append($('<div><input id="training" type="checkbox"/><label for="training">Training</label></div>'));
  }

  function update(board, all_taus, all_stale_taus, paused, target, wrong_property, scores, time, avg_number, number, ended, hint, player_rank_info, found_puzzle_taus, new_games, training_options, is_pausable) {
    game_paused = paused;
    if (hint !== null && tau_to_string(hint) !== last_hint_tau_string) {
      hints_given = 0;
      last_hint_tau_string = tau_to_string(hint);
    }
    if (debug) {
      console.log("Time since last submit: " + (new Date().getTime() - last_submit_time) + "ms");
    }
    all_tau_strings = {};
    for (var i in all_taus) {
      all_tau_strings[tau_to_string(all_taus[i])] = true;
    }
    all_stale_tau_strings = {};
    for (var i in all_stale_taus) {
      all_stale_tau_strings[tau_to_string(all_stale_taus[i])] = true;
    }
    game_ended = ended;
    update_scores(scores, ended, is_pausable);
    
    update_time(time, paused, avg_number, ended, player_rank_info);

    // update board
    stale_tau_to_index_map = {};
    var j = 0;
    for (var i in found_puzzle_taus) {
      stale_tau_to_index_map[tau_to_string(found_puzzle_taus[i])] = j;
      j++;
    }
    
    update_board(board, paused, target, wrong_property, number, hint, ended, found_puzzle_taus, training_options);
    update_buttons(ended, paused, is_pausable);

    if (ended) {
      update_new_game();
    }

    if (ended) {
      $("body").addClass("ended");
    }
  };

  game_type_info_map = {}
  for (var i = 0; i < game_type_info.length; i++) {
    game_type_info_map[game_type_info[i][0]] = game_type_info[i][1];
  }

  function update_messages(text_area, name, message, message_type) {
    var is_at_bottom = text_area[0].scrollHeight - text_area.scrollTop() <= text_area.outerHeight();
    if (message_type === "chat") {
      text_area.append($("<div class=\"message\"><span class=\"name\">" + name + ":</span> " + message + "</div>"));
    } else if (message_type === "status") {
      text_area.append($("<div class=\"message\"><span class=\"status\">" + message + "</span></div>"));
    } else if (message_type === "new_game") {
      text_area.append($('<div class="message"><span class="status">' + name + ' has started <a href="/game/' + message[1] + '">game ' + message[1] + '</a> (' + game_type_info_map[message[0]] + ')</span></div>'));
    }
    if (is_at_bottom) {
      text_area.scrollTop(text_area[0].scrollHeight - text_area.outerHeight() + 5);
    }
  }

  ws.onmessage = function (e) {
    var data = JSON.parse(e.data);
    if (data.type === "update") {
      var wrong_property = null;
      if (data.wrong_property !== null) {
        wrong_property = parseInt(data.wrong_property);
      }
      update(data.board, data.all_taus, data.all_stale_taus, data.paused, data.target, wrong_property, data.scores, data.time, data.avg_number, data.number, data.ended, data.hint, data.player_rank_info, data.found_puzzle_taus, data.new_games, data.training_options, data.is_pausable);
      ready();
    } else if (data.type === "scores") {
      update_scores(data.scores, data.ended);
      update_buttons(game_ended, game_paused, data.is_pausable);
    } else if (data.type == "chat") {
      var text_area = $("#chat");
      update_messages($("#chat"), data.name, data.message, data.message_type);
    } else if (data.type === "history") {
      var text_area = $("#chat");
      text_area.html("");
      data.messages.forEach(function(chat_message) {
        update_messages(text_area, chat_message[0], chat_message[1], chat_message[2]);
      });
      $("#chat_box").removeAttr("disabled");
      $("#say").removeAttr("disabled");
      ready();
    } else if (data.type === "old_found_puzzle_tau") {
      var found_puzzle_taus = $($(".found_puzzle_tau")[data.index]).find(".smallCard").each(function (index, raw_card) {
        var card  = $(raw_card);
        card.stop();
        card.css("background-color", "#FBB");
        card.animate({backgroundColor: "#FBB"}, 200)
            .animate({backgroundColor: "#FFF"}, 1000);
      });
      deselect_all_cards();
    } else if (data.type === "training_options") {
      var options = data.options;
      if ($('#property_picker')) {
        if (options.property === null) {
          $('#property_picker').val("all");
        } else {
          $('#property_picker').val(options.property);
        }
      }
    }
  }

  ws.onclose = function() {
    $("body").prepend($("<span>DISCONNECTED - <a href=\"javascript:location.reload(true)\">REFRESH</a> (if you can't connect at all, <a href=\"" + window.location.href.replace("http:", "https:") + "\">try https</a> (ignore any warnings you see, my certificate is not good))</span>"));
    $("body").css("background-color", "red");
  };

  // CHAT

  function on_chat(e) {
    var chat_box = $("#chat_box");
    if (chat_box.val() && (e.type == "click" || e.keyCode === 13)) {
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
