$(document).ready(function() {
  $("#testframe").load(function() {
    run_test($("#testframe"));
  });
});

function run_test(iframe) {
  run_actions(iframe, [new_game_function("3tau"), start_game, select_card_function([2, 2, 0, 2])]);
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

function new_game_function(game_type) {
  return function(doc, callback) {
    doc.find("#new_" + game_type).click();
    callback();
  }
}

var timeout = undefined;

function start_game(doc, callback) {
  if (doc.find("#waiting").length === 0 || doc.find("#waiting").text() === "waiting") {
    clearTimeout(timeout);
    timeout = setTimeout(function() {
      start_game(doc, callback);
    }, 500);
  } else {
    doc.find("#start")[0].click();
    callback();
  }
}

function select_card_function(card) {
  return function select_card(doc, callback) {
    if (doc.find("#waiting").length === 0 || doc.find("#waiting").text() === "waiting") {
      clearTimeout(timeout);
      timeout = setTimeout(function() {
        select_card(doc, callback);
      }, 500);
    } else {
      console.log(doc.find('div[data-card="' + card.join() + '"]')[0]);
      doc.find('div[data-card="' + card.join() + '"]')[0].click();
      callback();
    }
  }
}
