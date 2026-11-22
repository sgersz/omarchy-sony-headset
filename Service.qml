import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import "Model.js" as Model

QtObject {
  id: root
  property var state: ({})
  property bool available: false
  property string error: ""
  property string commandError: ""
  property int revision: 0
  property string pendingMethod: ""
  signal commandFinished(string method, bool success)
  readonly property bool busy: action.running || restart.running
  readonly property string helper: decodeURIComponent(String(Qt.resolvedUrl("bridge.py")).replace(/^(file|qs):\/\//, ""))

  function accept(raw, command) {
    try {
      if (raw.length > 65536) throw new Error("Sony response is too large");
      var result = JSON.parse(raw);
      if (result.ok !== true) throw new Error(Model.text(result.error && result.error.message, 240) || "Sony request failed");
      state = Model.reconcile(state, result.data);
      available = true;
      error = "";
      if (command) commandError = "";
      revision++;
      return true;
    } catch (e) {
      if (command) commandError = Model.text(String(e), 240);
      else { available = false; error = Model.text(String(e), 240); }
      return false;
    }
  }
  function refresh() {
    if (!poll.running && !busy) poll.running = true;
  }
  function send(method, params) {
    if (busy || !available || state.connected !== true) return false;
    commandError = "";
    pendingMethod = method;
    action.command = ["python3", helper, method, JSON.stringify(params)];
    action.running = true;
    return true;
  }
  function restartBackend() {
    if (!busy) { commandError = ""; restart.running = true; }
  }
  property Process poll: Process {
    command: ["python3", root.helper, "snapshot"]
    stdout: StdioCollector { onStreamFinished: root.accept(text, false) }
  }
  property Process action: Process {
    stdout: StdioCollector { id: actionOutput; waitForEnd: true }
    onExited: {
      var success = root.accept(actionOutput.text, true);
      var method = root.pendingMethod;
      root.pendingMethod = "";
      root.commandFinished(method, success);
      refreshLater.restart();
    }
  }
  property Process restart: Process {
    command: ["systemctl", "--user", "restart", "sonyd.service"]
    stderr: StdioCollector { id: restartError; waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) root.commandError = Model.text(restartError.text, 240) || "Could not restart sonyd.service";
      refreshLater.restart();
    }
  }
  property Timer refreshLater: Timer { interval: 700; onTriggered: root.refresh() }
  property Timer timer: Timer { interval: 4000; repeat: true; running: true; triggeredOnStart: true; onTriggered: root.refresh() }
  property ShellIpc ipc: ShellIpc {
    target: "steve.sony.backend"
    function status(): string { return JSON.stringify({available: root.available, busy: root.busy, error: root.error, commandError: root.commandError, state: root.state}); }
    function refresh(): void { root.refresh(); }
  }
}
