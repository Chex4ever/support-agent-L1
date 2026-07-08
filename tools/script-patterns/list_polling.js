// === Pattern: Token Polling for List ===
// Use when: List items lose token bindings after .Clone()
// Context: Buttons use GUI actions (number_to_tag) that bypass scripts
// Solution: Poll token value every 500ms and update cloned items manually
//
// Instructions:
// 1. Replace "Page 1" / "Item 1" / "Popup 1" with your actual names
// 2. Replace "Item 1" inside the popup with the actual label name
// 3. Replace "Tokens.test" with your actual token name

var pollLabels = [];
var pollLastValue = "";

IR.AddListener(IR.EVENT_START, 0, function () {
  var list = IR.GetItem("Page 1").GetItem("Item 1");
  var template = IR.GetItem("Popup 1");

  list.Clear();

  for (var i = 0; i < 4; i++) {
    var cloned = template.Clone("item_" + i);
    var label = cloned.GetItem("Item 1");
    pollLabels.push(label);

    list.CreateItem(i, 0, {
      Name: "listitem_" + i,
      Item: cloned
    });
  }

  IR.SetInterval(500, function () {
    var val = IR.GetVariable("Tokens.test");
    if (val !== pollLastValue) {
      pollLastValue = val;
      for (var i = 0; i < pollLabels.length; i++) {
        pollLabels[i].Text = val;
      }
    }
  });
});
