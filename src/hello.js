import { pathToFileURL } from "node:url";

export function greet(name = "workflow-lab") {
  if (typeof name !== "string" || name.trim() === "") {
    throw new TypeError("name must be a non-empty string");
  }
  return `hello ${name.trim()}`;
}

const isMain = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  console.log(greet());
}
