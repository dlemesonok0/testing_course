const { existsSync } = require("node:fs");
const { spawn } = require("node:child_process");

function detectPythonCommand() {
  const candidates = [
    "backend/.venv/bin/python",
    "backend/.venv/Scripts/python.exe",
    "python3",
    "python",
  ];
  return candidates.find((candidate) => existsSync(candidate)) ?? "python";
}

function run(command, args) {
  return spawn(command, args, { stdio: "inherit", shell: false });
}

const python = detectPythonCommand();
const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
const backend = run(python, [
  "-m",
  "uvicorn",
  "app.main:app",
  "--reload",
  "--log-level",
  "info",
  "--access-log",
  "--app-dir",
  "backend",
]);
const frontend = run(npmCommand, ["--prefix", "frontend", "run", "dev"]);

function handleSpawnError(processName) {
  return (error) => {
    console.error(`[dev] Failed to start ${processName}:`, error.message);
    process.exitCode = 1;
    shutdown();
  };
}

function shutdown() {
  backend.kill("SIGTERM");
  frontend.kill("SIGTERM");
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
backend.on("error", handleSpawnError("backend"));
frontend.on("error", handleSpawnError("frontend"));

backend.on("exit", (code) => {
  if (code && code !== 0) process.exitCode = code;
  shutdown();
});

frontend.on("exit", (code) => {
  if (code && code !== 0) process.exitCode = code;
  shutdown();
});
