console.log(`start script v2`);
const eventSource = new EventSource("/log-stream");
console.log(`connected EV log-stream`);
console.log(`get div messages`);
const messagesElementDiv = document.getElementById("messages");
var data = localStorage.getItem("sse log-stream");
if (data) {
  messagesElementDiv.innerHTML = data;
  console.log("data loaded from localStorage");
} else {
  console.log("data is missing from localStorage");
};

eventSource.onmessage = function(e) {
  console.log(`new data:`);
  console.log(e.data);
  messagesElementDiv.innerHTML = e.data;
  localStorage.setItem("sse log-stream",e.data);
};