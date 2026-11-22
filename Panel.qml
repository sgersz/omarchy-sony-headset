import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "steve.sony"
  ipcTarget: "steve.sony"
  manageIpc: false
  readonly property var backend: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
  readonly property var state: backend ? backend.state : ({})
  readonly property bool connected: !!backend && backend.available && state.connected === true
  readonly property bool busy: !!backend && backend.busy
  property string page: "noise"
  property var eqDraft: [0, 0, 0, 0, 0]
  property int bassDraft: 0
  property bool eqDirty: false
  property string eqDeviceKey: ""
  property string pendingEq: ""
  readonly property var ambientPreference: state.ambientPreference || ({level: 10, focusOnVoice: false})
  readonly property color fg: Commons.Color.popups.text
  readonly property var tabs: ["noise", "eq", "features"]
  readonly property real panelHeight: Style.space(page === "eq" || page === "features" ? 555 : 380)
  readonly property var presets: [
    {value:"0",label:strings.t("off")}, {value:"16",label:strings.t("bright")}, {value:"17",label:strings.t("excited")},
    {value:"18",label:strings.t("mellow")}, {value:"19",label:strings.t("relaxed")}, {value:"20",label:strings.t("vocal")},
    {value:"21",label:strings.t("trebleBoost")}, {value:"22",label:strings.t("bassBoost")},
    {value:"23",label:strings.t("speech")}, {value:"160",label:strings.t("manual")}
  ]
  Translations { id: strings; directory: Qt.resolvedUrl("i18n") }
  ShellIpc {
    target: root.ipcTarget
    function open(): void { root.open(); }
    function close(): void { root.close(); }
    function toggle(): void { root.toggle(); }
    function showPage(name: string): void {
      if (root.tabs.indexOf(name) >= 0) { root.page = name; root.open(); }
    }
    function status(): string { return JSON.stringify({page: root.page, connected: root.connected, eqDirty: root.eqDirty, pendingEq: root.pendingEq}); }
  }

  function cap(name) { return !!state.capabilities && state.capabilities[name] === true; }
  function valid(name) { return connected && !!state.features && !!state.features[name] && state.features[name].availability === "valid"; }
  function send(method, params) { return backend ? backend.send(method, params) : false; }
  function syncEq() {
    if (eqDeviceKey !== (state.deviceKey || "")) {
      eqDeviceKey = state.deviceKey || ""; eqDirty = false; pendingEq = "";
    }
    if (!eqDirty && pendingEq === "" && valid("equalizer") && state.equalizer && state.equalizer.bands.length === 5) {
      eqDraft = state.equalizer.bands.slice(); bassDraft = state.equalizer.clearBass;
    }
  }
  function applyEq(method, params) {
    pendingEq = method;
    if (!send(method, params)) pendingEq = "";
  }
  function setBand(index, value) {
    var draft = eqDraft.slice(); draft[index] = Math.round(value); eqDraft = draft; eqDirty = true;
  }
  function setMode(mode) {
    if (mode === "ambient") send("ambient", ambientPreference);
    else send("anc", {enabled: mode === "cancelling"});
  }
  function launchApp() { Quickshell.execDetached(["sony-device-center"]); root.close(); }
  function firmwareHelp() { Qt.openUrlExternally(Model.firmwareSupportUrl(state.name)); root.close(); }
  onOpenedChanged: if (opened) { if (backend) backend.refresh(); syncEq(); }
  Connections {
    target: root.backend
    function onRevisionChanged() { root.syncEq(); }
    function onCommandFinished(method, success) {
      if (root.pendingEq === method) {
        root.pendingEq = "";
        if (success) { root.eqDirty = false; root.syncEq(); }
      }
    }
  }
  implicitWidth: icon.implicitWidth
  implicitHeight: icon.implicitHeight

  BarIconButton {
    id: icon
    anchors.fill: parent
    bar: root.bar
    text: "󰋋"
    labelText: root.valid("battery") && root.state.battery.main !== null ? I18n.formatNumber(root.state.battery.main) + "%" : ""
    slotSize: labelText !== "" ? Style.bar.iconSlot * 2.4 : Style.bar.iconSlot
    tooltipText: Model.escapeTooltip((root.state.name || strings.t("title")) + " — " + (root.connected ? (root.valid("codec") ? root.state.codec : strings.t("connected")) : strings.t("disconnected")))
    onPressed: root.toggle()
  }

  KeyboardPanel {
    id: popup
    objectName: "headsetPopup"
    anchorItem: icon
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: popup.fittedContentWidth(Style.space(440))
    contentHeight: popup.fittedContentHeight(root.panelHeight)
    focusTarget: popup.loadedContent
    content: FocusScope {
      implicitHeight: root.panelHeight
      focus: true
      Keys.onEscapePressed: root.close()
      ColumnLayout {
        anchors.fill: parent
        spacing: Style.space(12)
        RowLayout {
          Layout.fillWidth: true
          PlainText { text: "󰋋"; font.pixelSize: Style.font.display }
          ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            PlainText { Layout.fillWidth: true; text: root.state.name || strings.t("title"); font.pixelSize: Style.font.subtitle; font.bold: true; elide: Text.ElideRight }
            PlainText {
              Layout.fillWidth: true
              text: root.connected ? strings.t("deviceInfo").arg(root.valid("codec") ? root.state.codec : strings.t("unknown")).arg(root.valid("firmware") ? root.state.firmware : strings.t("unknown")) : strings.t("disconnected")
              font.pixelSize: Style.font.caption
              opacity: 0.65
              elide: Text.ElideRight
            }
          }
          PlainText {
            text: root.valid("battery") && root.state.battery.main !== null ? I18n.formatNumber(root.state.battery.main) + "%" : "—"
            font.pixelSize: Style.font.title
            font.bold: true
          }
        }
        RowLayout {
          Layout.fillWidth: true
          Repeater {
            model: root.tabs
            Button {
              required property string modelData
              Layout.fillWidth: true
              text: strings.t(modelData)
              selected: root.page === modelData
              focusable: true
              onClicked: root.page = modelData
            }
          }
        }
        PlainText {
          Layout.fillWidth: true
          visible: !root.connected || !!(root.backend && (root.backend.commandError || root.backend.error))
          text: root.backend ? (root.backend.commandError || root.backend.error || (root.connected ? "" : root.state.lastError || strings.t("connecting"))) : strings.t("connecting")
          wrapMode: Text.Wrap
          font.pixelSize: Style.font.caption
          color: root.connected ? Commons.Color.urgent : root.fg
        }
        Controls.ScrollView {
          id: scroll
          Layout.fillWidth: true
          Layout.fillHeight: true
          clip: true
          contentWidth: availableWidth
          ColumnLayout {
            width: scroll.availableWidth
            spacing: Style.space(10)
            ColumnLayout {
              Layout.fillWidth: true
              visible: root.page === "noise"
              spacing: Style.space(12)
              PlainText { text: strings.t("listening"); font.bold: true }
              RowLayout {
                Layout.fillWidth: true
                enabled: root.valid("noiseControl") && !root.busy
                opacity: enabled ? 1 : 0.4
                Repeater {
                  model: ["cancelling", "ambient", "off"]
                  Button {
                    required property string modelData
                    Layout.fillWidth: true
                    text: strings.t(modelData)
                    selected: root.valid("noiseControl") && root.state.noiseControl.mode === modelData
                    visible: modelData === "off" || root.cap(modelData === "cancelling" ? "anc" : "ambient")
                    focusable: true
                    onClicked: root.setMode(modelData)
                  }
                }
              }
              ColumnLayout {
                Layout.fillWidth: true
                visible: root.cap("ambient")
                enabled: root.valid("noiseControl") && root.state.noiseControl.mode === "ambient" && !root.busy
                opacity: enabled ? 1 : 0.4
                PlainText { text: strings.t("ambientLevel").arg(I18n.formatNumber(root.ambientPreference.level)) }
                HeadsetSlider {
                  accessibleLabel: strings.t("ambient")
                  Layout.fillWidth: true
                  bar: root.bar
                  minimum: 1; maximum: 20; integer: true; step: 1
                  value: root.ambientPreference.level
                  onReleased: function(value) { root.send("ambient", {level: Math.round(value), focusOnVoice: root.state.noiseControl.focusOnVoice}); }
                }
                Toggle {
                  Layout.fillWidth: true
                  visible: root.cap("focusOnVoice")
                  label: strings.t("focusVoice")
                  checked: root.valid("noiseControl") && root.state.noiseControl.focusOnVoice
                  onClicked: root.send("ambient", {level: root.state.noiseControl.ambientLevel, focusOnVoice: !root.state.noiseControl.focusOnVoice})
                }
              }
              PlainText { Layout.fillWidth: true; text: strings.t("noiseHint"); opacity: 0.6; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap }
            }
            ColumnLayout {
              Layout.fillWidth: true
              visible: root.page === "eq"
              spacing: Style.space(9)
              PlainText { Layout.fillWidth: true; visible: !root.cap("equalizer") || root.cap("tenBandEqualizer"); text: strings.t("eqUnavailable"); wrapMode: Text.Wrap }
              Dropdown {
                id: presetDropdown
                objectName: "eqPreset"
                Layout.fillWidth: true
                visible: root.cap("equalizer") && !root.cap("tenBandEqualizer")
                label: strings.t("preset")
                options: root.presets
                enabled: root.valid("equalizer") && !root.busy
                value: root.state.equalizer ? String(root.state.equalizer.preset) : ""
                onChanged: function(value) {
                  root.applyEq("eqPreset", {preset: Number(value)});
                  presetDropdown.value = Qt.binding(function() { return root.state.equalizer ? String(root.state.equalizer.preset) : ""; });
                }
              }
              ColumnLayout {
                Layout.fillWidth: true
                visible: root.cap("equalizer") && !root.cap("tenBandEqualizer")
                enabled: root.valid("equalizer") && !root.busy
                opacity: enabled ? 1 : 0.4
                spacing: Style.space(5)
                Repeater {
                  model: ["400 Hz", "1 kHz", "2.5 kHz", "6.3 kHz", "16 kHz"]
                  ColumnLayout {
                    required property int index
                    required property string modelData
                    Layout.fillWidth: true
                    spacing: 0
                    RowLayout {
                      Layout.fillWidth: true
                      PlainText { text: modelData; font.pixelSize: Style.font.caption; Layout.fillWidth: true }
                      PlainText { text: I18n.formatNumber(root.eqDraft[index]) + " dB"; font.pixelSize: Style.font.caption }
                    }
                    HeadsetSlider {
                      accessibleLabel: modelData
                      Layout.fillWidth: true
                      bar: root.bar
                      minimum: -10; maximum: 10; step: 1; integer: true
                      value: root.eqDraft[index]
                      onMoved: function(value) { root.setBand(index, value); }
                    }
                  }
                }
                PlainText { text: strings.t("clearBass").arg(I18n.formatNumber(root.bassDraft)); visible: root.cap("clearBass"); font.pixelSize: Style.font.caption }
                HeadsetSlider {
                  accessibleLabel: strings.t("clearBassName")
                  Layout.fillWidth: true
                  visible: root.cap("clearBass")
                  bar: root.bar
                  minimum: -10; maximum: 10; step: 1; integer: true
                  value: root.bassDraft
                  onMoved: function(value) { root.bassDraft = Math.round(value); root.eqDirty = true; }
                }
                RowLayout {
                  Layout.fillWidth: true
                  Button { Layout.fillWidth: true; text: strings.t("applyEq"); enabled: root.eqDirty; focusable: true; onClicked: root.applyEq("eqCustom", {clearBass: root.bassDraft, bands: root.eqDraft}) }
                  Button { text: strings.t("discard"); enabled: root.eqDirty; focusable: true; onClicked: { root.eqDirty = false; root.syncEq(); } }
                }
              }
            }
            ColumnLayout {
              Layout.fillWidth: true
              visible: root.page === "features"
              spacing: Style.space(9)
              Repeater {
                model: ["dsee", "speakToChat", "adaptiveVolume"]
                ColumnLayout {
                  required property string modelData
                  Layout.fillWidth: true
                  visible: root.cap(modelData)
                  Toggle {
                    Layout.fillWidth: true
                    label: strings.t(modelData)
                    checked: root.valid(modelData) && root.state[modelData] === true
                    enabled: root.valid(modelData) && !root.busy
                    opacity: enabled ? 1 : 0.4
                    onClicked: root.send(modelData, {enabled: !root.state[modelData]})
                  }
                  PlainText {
                    Layout.fillWidth: true
                    visible: !root.valid(modelData)
                    text: strings.t("unavailable")
                    opacity: 0.6; font.pixelSize: Style.font.caption; wrapMode: Text.Wrap
                  }
                }
              }
              Dropdown {
                id: powerDropdown
                objectName: "autoPowerOff"
                Layout.fillWidth: true
                visible: root.cap("autoPowerOff")
                label: strings.t("autoPowerOff")
                enabled: root.valid("autoPowerOff") && !root.busy
                value: root.valid("autoPowerOff") ? String(root.state.autoPowerOff) : ""
                options: Model.powerOffModes().map(function(mode) {
                  return {value: String(mode.value), label: mode.count
                    ? strings.tn(mode.key, mode.count).arg(I18n.formatNumber(mode.count)) : strings.t(mode.key)};
                })
                onChanged: function(value) {
                  root.send("autoPowerOff", {index: Number(value)});
                  powerDropdown.value = Qt.binding(function() { return root.valid("autoPowerOff") ? String(root.state.autoPowerOff) : ""; });
                }
              }
              Button { Layout.fillWidth: true; text: strings.t("firmwareHelp"); focusable: true; onClicked: root.firmwareHelp() }
              PlainText { Layout.fillWidth: true; text: strings.t("firmwareHint"); wrapMode: Text.Wrap; font.pixelSize: Style.font.caption; opacity: 0.65 }
            }
          }
        }
        RowLayout {
          Layout.fillWidth: true
          Button { text: strings.t("refresh"); focusable: true; onClicked: if (root.backend) root.backend.refresh() }
          Button { text: strings.t("reconnect"); visible: !root.connected; focusable: true; onClicked: if (root.backend) root.backend.restartBackend() }
          Item { Layout.fillWidth: true }
          Button { text: strings.t("fullApp"); focusable: true; onClicked: root.launchApp() }
        }
      }
    }
  }
}
