$(document).ready(function() {
  $("#testframe").load(function() {
    run_test($("#testframe"));
  });
});

function run_test(iframe) {
  actions = [new_game_function(game_type), start_game];
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
