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
  return spawn(command, args, { stdio: "inherit" });
}

const python = detectPythonCommand();
const backend = run(python, ["-m", "uvicorn", "app.main:app", "--reload", "--log-level", "info", "--access-log", "--app-dir", "backend"]);
const frontend = run("npm", ["--prefix", "frontend", "run", "dev"]);

function shutdown() {
  backend.kill("SIGTERM");
  frontend.kill("SIGTERM");
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

backend.on("exit", (code) => {
  if (code && code !== 0) process.exitCode = code;
  shutdown();
});

frontend.on("exit", (code) => {
  if (code && code !== 0) process.exitCode = code;
  shutdown();
});
