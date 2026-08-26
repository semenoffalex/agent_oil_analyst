#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function fail(msg) {
  process.stderr.write(String(msg) + "\n");
  process.exit(1);
}

function posixPath(p) {
  return String(p || "").replace(/\\/g, "/");
}

function commonPrefix(paths) {
  if (!paths.length) return "";
  const split = paths.map((p) => posixPath(p).split("/").filter(Boolean));
  const minLen = Math.min(...split.map((s) => s.length));
  const prefix = [];
  for (let i = 0; i < minLen; i++) {
    const seg = split[0][i];
    if (split.every((s) => s[i] === seg) && split.every((s) => s.length > i + 1 || split.every((x) => x.length > i + 1))) {
      // only include a segment if ALL paths have a remaining segment after it
      if (split.every((s) => s.length > i + 1)) prefix.push(seg);
      else break;
    } else break;
  }
  return prefix.length ? prefix.join("/") + "/" : "";
}

const DIR_PATTERNS = [
  [["routes", "api", "controllers", "endpoints", "handlers", "controller", "routers", "serializers", "blueprints"], "api"],
  [["services", "core", "lib", "domain", "logic", "internal", "signals", "composables", "mailers", "jobs", "channels"], "service"],
  [["models", "db", "data", "persistence", "repository", "entities", "migrations", "entity", "sql", "database", "schema"], "data"],
  [["components", "views", "pages", "ui", "layouts", "screens"], "ui"],
  [["middleware", "plugins", "interceptors", "guards"], "middleware"],
  [["utils", "helpers", "common", "shared", "tools", "templatetags", "pkg"], "utility"],
  [["config", "constants", "env", "settings", "management", "commands"], "config"],
  [["__tests__", "test", "tests", "spec", "specs"], "test"],
  [["types", "interfaces", "schemas", "contracts", "dtos", "dto", "request", "response"], "types"],
  [["hooks"], "hooks"],
  [["store", "state", "reducers", "actions", "slices"], "state"],
  [["assets", "static", "public"], "assets"],
  [["cmd", "bin"], "entry"],
  [["docs", "documentation", "wiki"], "documentation"],
  [["deploy", "deployment", "infra", "infrastructure", "k8s", "kubernetes", "helm", "charts", "terraform", "tf", "docker"], "infrastructure"],
  [[".github", ".gitlab", ".circleci"], "ci-cd"],
];

function matchDirPattern(dirName) {
  const lower = String(dirName || "").toLowerCase();
  for (const [names, label] of DIR_PATTERNS) {
    if (names.includes(lower)) return label;
  }
  return null;
}

function fileLevelPattern(filePath, name) {
  const p = posixPath(filePath);
  const n = name || path.posix.basename(p);
  if (
    /\.test\./i.test(n) ||
    /\.spec\./i.test(n) ||
    /^test_.*\.py$/i.test(n) ||
    /_test\.go$/i.test(n) ||
    /Test\.java$/.test(n) ||
    /_spec\.rb$/i.test(n) ||
    /Test\.php$/.test(n) ||
    /Tests\.cs$/.test(n)
  )
    return "test";
  if (n.endsWith(".d.ts")) return "types";
  if (n === "Dockerfile" || /^docker-compose/i.test(n) || n === ".dockerignore") return "infrastructure";
  if (/\.tf$|\.tfvars$/i.test(n)) return "infrastructure";
  if (n === "Makefile") return "infrastructure";
  if (/\.sql$/i.test(n)) return "data";
  if (/\.(graphql|gql|proto)$/i.test(n)) return "types";
  if (/\.(md|rst)$/i.test(n)) return "documentation";
  if (["Cargo.toml", "go.mod", "Gemfile", "pom.xml", "build.gradle", "composer.json", "pyproject.toml"].includes(n))
    return "config";
  if (p.includes(".github/workflows/") || n === ".gitlab-ci.yml" || n === "Jenkinsfile") return "ci-cd";
  if (n === "wsgi.py" || n === "asgi.py") return "config";
  if (n === "manage.py") return "entry";
  if (n === "__init__.py" || n === "index.ts" || n === "index.js") return "entry";
  if (n === "__main__.py") return "entry";
  return null;
}

function main() {
  const inPath = process.argv[2];
  const outPath = process.argv[3];
  if (!inPath || !outPath) fail("Usage: ua-arch-analyze.js <input.json> <output.json>");

  let raw;
  try {
    raw = fs.readFileSync(inPath, "utf8");
  } catch (e) {
    fail("Failed to read input: " + e.message);
  }

  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    fail("Invalid JSON: " + e.message);
  }

  const fileNodes = Array.isArray(data.fileNodes) ? data.fileNodes : [];
  const importEdges = Array.isArray(data.importEdges) ? data.importEdges : [];
  const allEdges = Array.isArray(data.allEdges) ? data.allEdges : [];

  const paths = fileNodes.map((n) => posixPath(n.filePath || n.id.replace(/^[a-z]+:/, "")));
  const prefix = commonPrefix(paths);

  const directoryGroups = {};
  for (const n of fileNodes) {
    const fp = posixPath(n.filePath || "");
    let rest = fp;
    if (prefix && rest.startsWith(prefix)) rest = rest.slice(prefix.length);
    const segs = rest.split("/").filter(Boolean);
    const group = segs.length > 1 ? segs[0] : segs.length === 1 && rest.includes("/") ? segs[0] : "root";
    if (!directoryGroups[group]) directoryGroups[group] = [];
    directoryGroups[group].push(n.id);
  }

  const nodeTypeGroups = {};
  for (const n of fileNodes) {
    const t = n.type || "file";
    if (!nodeTypeGroups[t]) nodeTypeGroups[t] = [];
    nodeTypeGroups[t].push(n.id);
  }

  const idToGroup = {};
  for (const [g, ids] of Object.entries(directoryGroups)) {
    for (const id of ids) idToGroup[id] = g;
  }

  const fileFanOut = {};
  const fileFanIn = {};
  const adj = {};
  for (const n of fileNodes) {
    fileFanOut[n.id] = 0;
    fileFanIn[n.id] = 0;
    adj[n.id] = [];
  }
  for (const e of importEdges) {
    if (!fileFanOut[e.source] && fileFanOut[e.source] !== 0) continue;
    fileFanOut[e.source] = (fileFanOut[e.source] || 0) + 1;
    fileFanIn[e.target] = (fileFanIn[e.target] || 0) + 1;
    if (!adj[e.source]) adj[e.source] = [];
    adj[e.source].push(e.target);
  }

  const groupImportFrom = {};
  const groupImportedBy = {};
  for (const g of Object.keys(directoryGroups)) {
    groupImportFrom[g] = new Set();
    groupImportedBy[g] = new Set();
  }
  const interMap = {};
  for (const e of importEdges) {
    const a = idToGroup[e.source];
    const b = idToGroup[e.target];
    if (!a || !b) continue;
    if (a !== b) {
      groupImportFrom[a].add(b);
      groupImportedBy[b].add(a);
      const k = a + " -> " + b;
      interMap[k] = (interMap[k] || 0) + 1;
    }
  }
  const interGroupImports = Object.entries(interMap)
    .map(([k, count]) => {
      const [from, to] = k.split(" -> ");
      return { from, to, count };
    })
    .sort((x, y) => y.count - x.count);

  const intraGroupDensity = {};
  for (const g of Object.keys(directoryGroups)) {
    let internal = 0;
    let total = 0;
    for (const e of importEdges) {
      const a = idToGroup[e.source];
      const b = idToGroup[e.target];
      if (a === g || b === g) {
        total++;
        if (a === g && b === g) internal++;
      }
    }
    intraGroupDensity[g] = {
      internalEdges: internal,
      totalEdges: total,
      density: total ? Number((internal / total).toFixed(4)) : 0,
    };
  }

  const crossMap = {};
  const idToType = {};
  for (const n of fileNodes) idToType[n.id] = n.type || "file";
  for (const e of allEdges) {
    const ft = idToType[e.source];
    const tt = idToType[e.target];
    if (!ft || !tt) continue;
    const k = ft + "|" + tt + "|" + (e.type || "related");
    crossMap[k] = (crossMap[k] || 0) + 1;
  }
  const crossCategoryEdges = Object.entries(crossMap).map(([k, count]) => {
    const [fromType, toType, edgeType] = k.split("|");
    return { fromType, toType, edgeType, count };
  });

  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    patternMatches[g] = matchDirPattern(g) || (g === "root" ? "root" : "unknown");
  }

  const infraFiles = [];
  let hasDockerfile = false;
  let hasCompose = false;
  let hasK8s = false;
  let hasTerraform = false;
  let hasCI = false;
  const schemaFiles = [];
  const migrationFiles = [];
  const dataModelFiles = [];
  const apiHandlerFiles = [];

  for (const n of fileNodes) {
    const fp = posixPath(n.filePath || "");
    const nm = n.name || path.posix.basename(fp);
    if (/Dockerfile/i.test(nm) || /Dockerfile/i.test(fp)) {
      hasDockerfile = true;
      infraFiles.push(fp);
    }
    if (/docker-compose/i.test(nm) || /docker-compose/i.test(fp)) {
      hasCompose = true;
      infraFiles.push(fp);
    }
    if (/\.tf$|\.tfvars$/i.test(nm)) {
      hasTerraform = true;
      infraFiles.push(fp);
    }
    if (/k8s|kubernetes|helm/i.test(fp)) {
      hasK8s = true;
      infraFiles.push(fp);
    }
    if (fp.includes(".github/workflows") || nm === ".gitlab-ci.yml" || nm === "Jenkinsfile") {
      hasCI = true;
      infraFiles.push(fp);
    }
    if (nm === "Makefile" || /deploy\//.test(fp) || /^docker\//.test(fp) || /\.dockerignore$/.test(nm)) {
      if (!infraFiles.includes(fp)) infraFiles.push(fp);
    }
    if (/\.(graphql|gql|proto|prisma)$/i.test(nm) || /schema\.(sql|yml|yaml)$/i.test(nm)) schemaFiles.push(fp);
    if (/migrat/i.test(fp) && /\.sql$/i.test(nm)) migrationFiles.push(fp);
    if (/models?\//i.test(fp) || /_model\.py$/i.test(nm)) dataModelFiles.push(fp);
    if (/routes?\/|controllers?\/|handlers?\/|endpoints?\//i.test(fp)) apiHandlerFiles.push(fp);
    const flp = fileLevelPattern(fp, nm);
    n._filePattern = flp;
  }

  const groupsWithReadme = new Set();
  const docsRefs = {};
  for (const n of fileNodes) {
    const fp = posixPath(n.filePath || "");
    const g = idToGroup[n.id];
    if (/README\.md$/i.test(fp)) groupsWithReadme.add(g);
  }
  const totalGroups = Object.keys(directoryGroups).length;
  const undocumentedGroups = Object.keys(directoryGroups).filter((g) => !groupsWithReadme.has(g));
  const docCoverage = {
    groupsWithDocs: groupsWithReadme.size,
    totalGroups,
    coverageRatio: totalGroups ? Number((groupsWithReadme.size / totalGroups).toFixed(4)) : 0,
    undocumentedGroups,
  };

  const depPairs = {};
  for (const row of interGroupImports) {
    const fwd = row.from + "|" + row.to;
    const rev = row.to + "|" + row.from;
    if (!depPairs[fwd] && !depPairs[rev]) depPairs[fwd] = { a: row.from, b: row.to, ab: 0, ba: 0 };
    const key = depPairs[fwd] ? fwd : depPairs[rev] ? rev : fwd;
    if (!depPairs[key]) depPairs[key] = { a: row.from, b: row.to, ab: 0, ba: 0 };
    if (row.from === depPairs[key].a) depPairs[key].ab += row.count;
    else depPairs[key].ba += row.count;
  }
  const dependencyDirection = [];
  for (const { a, b, ab, ba } of Object.values(depPairs)) {
    if (ab > ba) dependencyDirection.push({ dependent: a, dependsOn: b });
    else if (ba > ab) dependencyDirection.push({ dependent: b, dependsOn: a });
  }

  const filesPerGroup = {};
  for (const [g, ids] of Object.entries(directoryGroups)) filesPerGroup[g] = ids.length;
  const nodeTypeCounts = {};
  for (const [t, ids] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = ids.length;

  const filePatterns = {};
  for (const n of fileNodes) {
    const fp = posixPath(n.filePath || "");
    filePatterns[n.id] = {
      group: idToGroup[n.id],
      type: n.type,
      filePath: fp,
      filePattern: fileLevelPattern(fp, n.name || path.posix.basename(fp)),
      tags: n.tags || [],
    };
  }

  const out = {
    scriptCompleted: true,
    commonPrefix: prefix,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    deploymentTopology: {
      hasDockerfile,
      hasCompose,
      hasK8s,
      hasTerraform,
      hasCI,
      infraFiles,
    },
    dataPipeline: { schemaFiles, migrationFiles, dataModelFiles, apiHandlerFiles },
    docCoverage,
    dependencyDirection,
    fileStats: {
      totalFileNodes: fileNodes.length,
      filesPerGroup,
      nodeTypeCounts,
    },
    fileFanIn,
    fileFanOut,
    groupImportFrom: Object.fromEntries(
      Object.entries(groupImportFrom).map(([k, v]) => [k, [...v]])
    ),
    groupImportedBy: Object.fromEntries(
      Object.entries(groupImportedBy).map(([k, v]) => [k, [...v]])
    ),
    filePatterns,
  };

  try {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
  } catch (e) {
    fail("Failed to write output: " + e.message);
  }
}

main();
