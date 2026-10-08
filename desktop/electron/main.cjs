const { app, BrowserWindow, Tray, Menu, nativeImage, session } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

const RUNTIME_PORT = 7420;
const isDev = !app.isPackaged;

let mainWindow = null;
let tray = null;
let sidecar = null;
let quitting = false;

function runtimeHealth() {
  return new Promise((resolve) => {
    const req = http.get({ host: "127.0.0.1", port: RUNTIME_PORT, path: "/health", timeout: 400 }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForRuntime(tries = 40) {
  for (let i = 0; i < tries; i++) {
    if (await runtimeHealth()) return true;
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
}

function startSidecar() {
  const runtimeDir = path.join(__dirname, "../../runtime");
  sidecar = spawn("python3", ["-m", "charlie"], {
    cwd: runtimeDir,
    env: {
      ...process.env,
      PYTHONPATH: path.join(runtimeDir, "src"),
      KMP_DUPLICATE_LIB_OK: "TRUE",
    },
    stdio: "inherit",
  });
  sidecar.on("exit", (code) => {
    if (!quitting) console.error("Charlie sidecar exited", code);
    sidecar = null;
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 880,
    height: 620,
    minWidth: 720,
    minHeight: 520,
    title: "Charlie",
    backgroundColor: "#2C2144",
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://127.0.0.1:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function createTray() {
  const image = nativeImage.createEmpty();
  tray = new Tray(image);
  tray.setToolTip("Charlie");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: "Show Charlie",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      { type: "separator" },
      {
        label: "Quit",
        click: () => {
          quitting = true;
          app.quit();
        },
      },
    ])
  );
  tray.on("click", () => {
    if (!mainWindow) return;
    if (mainWindow.isVisible()) mainWindow.hide();
    else mainWindow.show();
  });
}

app.whenReady().then(async () => {
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === "media" || permission === "audioCapture" || permission === "microphone");
  });
  session.defaultSession.setPermissionCheckHandler((_wc, permission) => {
    return permission === "media" || permission === "audioCapture" || permission === "microphone";
  });
  const already = await runtimeHealth();
  if (!already) startSidecar();
  await waitForRuntime();
  createWindow();
  createTray();
});

app.on("before-quit", () => {
  quitting = true;
  if (sidecar && !sidecar.killed) sidecar.kill();
});

app.on("window-all-closed", (e) => {
  e.preventDefault();
});
