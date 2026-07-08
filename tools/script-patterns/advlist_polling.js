// === Pattern: Token Polling for Advanced List ===
// Use when: Advanced List items lose token bindings after adapter clones them
// Context: Buttons use GUI actions (number_to_tag) that bypass scripts
// Solution: Poll token value every 500ms and update cloned items manually
//
// Instructions:
// 1. Replace "Page 1" / "Item 7" / "Popup 1" with your actual names
// 2. Replace "Item 1" inside the popup with the actual label name
// 3. Replace "Tokens.test" with your actual token name
// 4. Adjust 'total: 4' to match your item count

var advPollLabels = [];
var advPollLastValue = "";

IR.AddListener(IR.EVENT_START, 0, function () {
  var advList = IR.GetItem("Page 1").GetItem("Item 7");
  var template = IR.GetItem("Popup 1");

  advList.SelectMode = 1;
  advList.Direction = 1;

  advList.Adapter = {
    total: 4,

    GetCount: function () {
      return this.total;
    },

    GetItem: function (pos) {
      var item = template.Clone("adv_item_" + pos);
      advPollLabels.push(item.GetItem("Item 1"));

      IR.AddListener(IR.EVENT_ITEM_RELEASE, item, function () {
        advList.SetSelected(item);
      });

      return item;
    },

    SetSelected: function (item, selected) {
      if (selected === true) {
        IR.Log("Selected: " + item.Name);
      }
    }
  };

  advList.Update();

  IR.SetInterval(500, function () {
    var val = IR.GetVariable("Tokens.test");
    if (val !== advPollLastValue) {
      advPollLastValue = val;
      for (var i = 0; i < advPollLabels.length; i++) {
        advPollLabels[i].Text = val;
      }
    }
  });
});
