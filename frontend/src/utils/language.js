const FILE_LANGUAGE_MAP = {
  ".py": "Python",
  ".js": "JavaScript",
  ".jsx": "JavaScript",
  ".ts": "TypeScript",
  ".tsx": "TypeScript",
  ".java": "Java",
  ".go": "Go",
  ".rs": "Rust",
  ".rb": "Ruby",
  ".php": "PHP",
  ".cs": "C#",
  ".cpp": "C++",
  ".json": "JSON",
  ".sql": "SQL",
  ".html": "HTML",
  ".css": "CSS",
  ".toml": "TOML",
  ".yml": "YAML",
  ".yaml": "YAML",
};

const NAMED_LANGUAGE_MAP = {
  "package.json": "JavaScript",
  "package-lock.json": "JavaScript",
  "pnpm-lock.yaml": "JavaScript",
  "yarn.lock": "JavaScript",
  "requirements.txt": "Python",
  "pyproject.toml": "Python",
  "poetry.lock": "Python",
  "go.mod": "Go",
  "cargo.toml": "Rust",
  "pom.xml": "Java",
  "composer.json": "PHP",
  gemfile: "Ruby",
};

export const detectLanguageFromFilename = (filename = "") => {
  const lowered = filename.trim().toLowerCase();
  if (NAMED_LANGUAGE_MAP[lowered]) {
    return NAMED_LANGUAGE_MAP[lowered];
  }

  const extensionMatch = lowered.match(/\.[^.]+$/);
  if (!extensionMatch) {
    return "Text";
  }
  return FILE_LANGUAGE_MAP[extensionMatch[0]] || "Text";
};

export const detectLanguageFromCode = (code = "") => {
  const lowered = code.toLowerCase();
  const heuristics = [
    ["Python", ["def ", "import ", "from ", "if __name__"]],
    ["JavaScript", ["const ", "let ", "=>", "console.log", "function "]],
    ["TypeScript", ["interface ", "type ", ": string", ": number", "implements "]],
    ["Java", ["public class ", "system.out.println", "public static void main"]],
    ["Go", ["package main", "func main()", "fmt."]],
    ["Rust", ["fn main()", "println!", "let mut "]],
    ["PHP", ["<?php", "$_post", "$_get", "echo "]],
    ["SQL", ["select ", "insert into ", "update ", "delete from "]],
    ["HTML", ["<!doctype html", "<html", "<div", "<body"]],
    ["CSS", ["color:", "display:", "@media", "font-family:"]],
  ];

  let best = { label: "Text", score: 0 };
  heuristics.forEach(([label, tokens]) => {
    const score = tokens.reduce((total, token) => total + (lowered.includes(token) ? 1 : 0), 0);
    if (score > best.score) {
      best = { label, score };
    }
  });
  return best.label;
};
