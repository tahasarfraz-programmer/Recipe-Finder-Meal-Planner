// Auto-dismiss flash messages, and confirm destructive actions.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".alert[data-autodismiss]").forEach(function (el) {
    setTimeout(function () {
      bootstrap.Alert.getOrCreateInstance(el).close();
    }, 5000);
  });

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });
});
