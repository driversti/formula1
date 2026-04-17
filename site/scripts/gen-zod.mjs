// Reads ../precompute/out/schema.json and writes src/lib/schemas.ts.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import jsonSchemaToZod from "json-schema-to-zod";

const here = dirname(fileURLToPath(import.meta.url));
const schemaPath = resolve(here, "../../precompute/out/schema.json");
const outPath = resolve(here, "../src/lib/schemas.ts");

const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const zodSource = jsonSchemaToZod(schema, { name: "ManifestSchema", module: "esm" });

const header = `// AUTO-GENERATED from precompute/out/schema.json — do not edit by hand.\n// Regenerate with: npm run gen:zod\n\n`;
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, header + zodSource + "\nexport type Manifest = import(\"zod\").z.infer<typeof ManifestSchema>;\n", "utf8");
console.log(`wrote ${outPath}`);
