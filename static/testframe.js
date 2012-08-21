$(document).ready(function() {
  if (game_type !== "all") {
    run_frame(game_type);
  } else {
    var timeout = 0;
    for (var type in game_type_to_taus) {
      setTimeout(run_frame_function(type), timeout);
      timeout += 1000;
    }
  }
});

function run_frame_function(type) {
  return function() {
    var iframe = $('<iframe id="testframe_"' + type + ' width=1024 height=768 src="http://localhost"></iframe>');
    $("body").append(iframe);
    iframe.load(function() {
      new Test().run_test(iframe, type, game_type_to_taus[type]);
    });
  }
}

function Test() {
  function run_test(iframe, type, taus) {
    var actions = [new_game_function(type), start_game];
    $.each(taus, function(i, tau) {
      $.each(tau, function(j, card) {
        actions.push(select_card_function(card));
      });
    });
    run_actions(iframe, actions);
  }

  function run_actions(iframe, actions) {
    if (actions.length !== 0) {
      actions[0](iframe.contents(), function() {
        if (actions.length !== 1) {
          run_actions(iframe, actions.slice(1, actions.length));
        }
      });
    }
  }

  var timeout = undefined;

  function wait(action, doc, callback) {
    if (doc.find("#waiting").length === 0 || doc.find("#waiting").text() === "waiting") {
      clearTimeout(timeout);
      timeout = setTimeout(function() {
        wait(action, doc, callback);
      }, 500);
    } else {
      action(doc, callback)
    }
  }

  function new_game_function(game_type) {
    return function(doc, callback) {
      doc.find("#new_" + game_type).click();
      callback();
    }
  }

  function start_game(doc, callback) {
    wait(function() {
      doc.find("#start")[0].click();
      callback();
    }, doc, callback);
  }

  function select_card_function(card) {
    return function select_card(doc, callback) {
      wait(function() {
        console.log("Looking for card: " + card);
        console.log(doc.find('div[data-card="' + card.join() + '"]')[0]);
        doc.find('div[data-card="' + card.join() + '"]')[0].click();
        callback();
      }, doc, callback);
    }
  }

  return {
    'run_test' : run_test,
  }
}
