const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("charlie", {
  runtimeUrl: "ws://127.0.0.1:7420/ws",
});
