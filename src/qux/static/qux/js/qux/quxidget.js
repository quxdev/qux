function maxSelectorHeight(selector) {
  return Math.max.apply(null, $(selector).map(function () {
    return $(this).height();
  }).get());
}

function equalizeSelectorHeights(selector) {
  let maxHeight = maxSelectorHeight(selector);
  $(selector).each(function () {
    $(this).css('height', maxHeight + "px");
  });
}

function unsetSelectorHeights(selector) {
  $(selector).each(function () {
    $(this).css('height', "");
  });
}

function sizePricingCards() {
  console.log('sizePricingCards');
  if ($(window).width() > 991) {
    equalizeSelectorHeights('.pricing-description');
    equalizeSelectorHeights('.pricing-features');
  } else {
    unsetSelectorHeights('.pricing-description');
    unsetSelectorHeights('.pricing-features');
  }
}
