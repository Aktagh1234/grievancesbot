document.addEventListener("DOMContentLoaded", function () {
  const convoButton = document.querySelector(".convo");

  // convoButton.addEventListener("click", function () {
  //   alert("Chatbot starting... (you can plug in your bot here!)");

  // });

  if (window.location.hash) {
    history.replaceState(null, null, ' ');
    window.scrollTo(0, 0);
  }
});

