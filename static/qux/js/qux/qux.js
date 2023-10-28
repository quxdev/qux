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

// Enable tooltips
// Bootstrap 4.6
document.addEventListener("DOMContentLoaded", function() {
  let tooltipList = document.querySelectorAll("[data-toggle=tooltip]");
  tooltipList.forEach(function(element) {
    element.tooltip();
  });
});

// Bootstrap 5.2.3
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
const tooltipList = [...tooltipTriggerList].map(
  tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl, {})
);

