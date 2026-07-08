// === Pattern: Custom Token Event Bus (Pub/Sub) ===
// Use when: You control all token writes via script (no GUI number_to_tag actions)
// Solution: Wrap IR.SetVariable in TokenSet() which notifies subscribers
// WARNING: Does NOT intercept GUI actions like number_to_tag — those bypass scripts
//
// Instructions:
// 1. Replace "Tokens.test" with your token name
// 2. Replace "Popup 1" / "Item 1" with your actual names
// 3. Replace IR.SetVariable("Tokens.X", v) calls with TokenSet("X", v)
// 4. Add as many TokenOn listeners as needed

var _tokenBus = {};

function TokenOn(name, callback) {
  if (!_tokenBus[name]) _tokenBus[name] = [];
  _tokenBus[name].push(callback);
}

function TokenSet(name, value) {
  IR.SetVariable("Tokens." + name, value);
  var list = _tokenBus[name];
  if (list) {
    for (var i = 0; i < list.length; i++) {
      list[i](value);
    }
  }
}

// ---- Example usage ----

IR.AddListener(IR.EVENT_START, 0, function () {
  var advList = IR.GetItem("Page 1").GetItem("Item 7");
  var template = IR.GetItem("Popup 1");
  var items = [];

  advList.SelectMode = 1;
  advList.Direction = 1;
  advList.Adapter = {
    total: 4,
    GetCount: function () { return this.total; },
    GetItem: function (pos) {
      var item = template.Clone("item_" + pos);
      items.push(item.GetItem("Item 1"));
      return item;
    },
    SetSelected: function (item, selected) { }
  };
  advList.Update();

  // Subscribe to "test" token changes
  TokenOn("test", function (value) {
    for (var i = 0; i < items.length; i++) {
      items[i].Text = value;
    }
  });
});

// Instead of: IR.SetVariable("Tokens.test", "1");
// Use:        TokenSet("test", "1");
