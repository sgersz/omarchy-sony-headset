import QtQuick
import qs.Ui
import qs.Commons
import qs.Commons as Commons

PanelSlider {
  id: root
  property string accessibleLabel: ""
  activeFocusOnTab: true
  Accessible.role: Accessible.Slider
  Accessible.name: accessibleLabel
  Keys.onPressed: function(event) {
    var key = Util.readingKey(event);
    var next = liveValue;
    if (key === Qt.Key_Left || key === Qt.Key_Down) next -= step;
    else if (key === Qt.Key_Right || key === Qt.Key_Up) next += step;
    else if (key === Qt.Key_Home) next = minimum;
    else if (key === Qt.Key_End) next = maximum;
    else return;
    next = Math.max(minimum, Math.min(maximum, integer ? Math.round(next) : next));
    liveValue = next;
    moved(next);
    released(next);
    event.accepted = true;
  }
  Rectangle {
    anchors.fill: parent
    color: "transparent"
    border.width: root.activeFocus ? 1 : 0
    border.color: Commons.Color.accent
    radius: Style.cornerRadius
  }
}
