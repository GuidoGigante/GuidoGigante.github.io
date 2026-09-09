// Publication filter. No dependencies, no build step.
(function () {
  var buttons = document.querySelectorAll('.filters button');
  var pubs = document.querySelectorAll('.pub');
  var years = document.querySelectorAll('.year');
  var empty = document.querySelector('.empty');

  function apply(filter) {
    pubs.forEach(function (pub) {
      var show = filter === 'all'
        || (filter === 'selected' && pub.dataset.selected === 'true')
        || pub.dataset.type === filter;
      pub.hidden = !show;
    });
    var any = false;
    years.forEach(function (year) {
      var visible = year.querySelectorAll('.pub:not([hidden])').length > 0;
      year.hidden = !visible;
      any = any || visible;
    });
    if (empty) empty.hidden = any;
  }

  buttons.forEach(function (button) {
    button.addEventListener('click', function () {
      buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b === button)); });
      apply(button.dataset.filter);
    });
  });
})();
