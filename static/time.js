$(function() {
  $.ajax({
    type: 'POST',
    url: '/time',
    data: {
      time_offset : new Date().getTimezoneOffset()
    },
  });
});
