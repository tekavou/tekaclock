var polling = false;
var pollingTimer = null;
var pollingStop = null;
var activeXhr = null;
var frame = null;
var indicator = null;
var currentFaceIdx = -1;
var faces = [];

function setFace(idx) {
  currentFaceIdx = idx;
  if (frame && faces[idx]) {
    stopPolling();
    frame.src = 'faces/' + faces[idx] + "/index.html?t=" + new Date().getTime();
    frame.onload = function () {
      try {
        if (frame.contentWindow && typeof frame.contentWindow.initFace === 'function') {
          frame.contentWindow.initFace();
        }
      } catch (e) {
        console.error("initFace error:", e);
      }
      startPolling(10000);
    };
  }
}

function wipeToFace(newIdx) {
  var overlay = document.getElementById("tapOverlay");
  if (!faces[newIdx]) return;

  overlay.style.transition = "height 0.5s linear, opacity 0.2s ease";
  overlay.style.webkitTransition = "height 0.5s linear, opacity 0.2s ease";
  overlay.style.height = "100%";
  overlay.style.opacity = "1";

  setTimeout(function () {
    if (newIdx !== currentFaceIdx) {
      setFace(newIdx);
    }

    setTimeout(function () {
      overlay.style.height = "0%";
      overlay.style.opacity = "0.01"; // still clickable
      overlay.style.height = "100%";
    }, 500);
  }, 500);
}

function stopPolling() {
  
  polling = false;
  if (activeXhr) activeXhr.abort();
  clearTimeout(pollingTimer);
  clearTimeout(pollingStop);
  if (indicator) indicator.style.display = "none";
  
}

function startPolling(durationMs) {
  
  if (polling) return;

  polling = true;
  if (indicator) indicator.style.display = "block";

  function poll() {    
    activeXhr = new XMLHttpRequest();
    activeXhr.open("GET", "/current_face?last=" + currentFaceIdx, true);
    activeXhr.onreadystatechange = function () {
      if (activeXhr.readyState === 4 && activeXhr.status === 200) {
        try {
          var d = JSON.parse(activeXhr.responseText);
          var newIdx = parseInt(d.current, 10);
          if (newIdx !== currentFaceIdx) {
            wipeToFace(newIdx);
          }
        } catch (e) {
          document.body.innerHTML += "<pre style='color:red'>Poll error: " + e + "</pre>";
        }
      }
    };
    activeXhr.send();

    if (polling) {
      pollingTimer = setTimeout(poll, 2000);
    }
  }

  poll();

  pollingStop = setTimeout(function () {
    stopPolling();
  }, durationMs);
}

(function () {
  frame = document.getElementById("faceFrame");
  indicator = document.getElementById("poll-indicator");

  var req = new XMLHttpRequest();
  req.open("GET", "/faces.json", true);
  req.onreadystatechange = function () {
    if (req.readyState === 4 && req.status === 200) {
      try {
        var data = JSON.parse(req.responseText);
        faces = data.faces;
        wipeToFace(data.current);
      } catch (e) {
        document.body.innerHTML += "<pre style='color:red'>Init error: " + e + "</pre>";
      }
    }
  };
  req.send();

  document.getElementById("tapOverlay").addEventListener("click", function () {
    console.log("Tap detected");
    if (polling) {
      stopPolling();
    } else {
      startPolling(10000);
    }
  });
  window.onunload = window.onbeforeunload = function () {
    stopPolling();
  };
})();