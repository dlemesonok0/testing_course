const { existsSync } = require("node:fs");
const { spawn } = require("node:child_process");
const { resolve } = require("node:path");

function detectPythonCommand() {
  const candidates = [
    "backend/.venv/bin/python.exe",
    "backend/.venv/bin/python",
    "backend/.venv/Scripts/python.exe",
    "python3",
    "python",
  ];
  return candidates.find((candidate) => existsSync(candidate)) ?? "python";
}

const backend = spawn(
  detectPythonCommand(),
  [
    "-m",
    "uvicorn",
    "app.main:app",
    "--reload",
    "--port",
    "8001",
    "--log-level",
    "info",
    "--access-log",
    "--app-dir",
    "backend",
  ],
  {
    env: {
      ...process.env,
      RECIPE_BOOK_DB_PATH: resolve("backend", "preprod_recipe_book.db"),
    },
    stdio: "inherit",
    shell: false,
  },
);

backend.on("exit", (code) => {
  if (code && code !== 0) process.exitCode = code;
});

process.on("SIGINT", () => backend.kill("SIGTERM"));
process.on("SIGTERM", () => backend.kill("SIGTERM"));
