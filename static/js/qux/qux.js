/*!
 * Qux JavaScript Library v0.0.1
 * https://qux.dev/qux/
 *
 * Copyright QuxDev
 * https://qux.dev/license
 *
 * Date: 2022-01-01
 */


function quxDeleteObject(elementId, deleteURL) {
  let csrftoken = $( "input[name=csrfmiddlewaretoken]" ).val();

  // HTTP methods that do not require CSRF protection
  function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      // if not safe, set csrftoken
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  $.ajax({
    method: "POST",
    url: deleteURL,
    success: function(result) {
      $("#" + elementId).remove();
      },
  });
}
