#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

function fail(msg) {
  process.stderr.write(String(msg) + "\n");
  process.exit(1);
}

const CODE_ENTRY_NAMES = new Set([
  "index.ts",
  "index.js",
  "main.ts",
  "main.js",
  "app.ts",
  "app.js",
  "server.ts",
  "server.js",
  "mod.rs",
  "main.go",
  "main.py",
  "main.rs",
  "manage.py",
  "app.py",
  "wsgi.py",
  "asgi.py",
  "run.py",
  "__main__.py",
  "Application.java",
  "Main.java",
  "Program.cs",
  "config.ru",
  "index.php",
  "App.swift",
  "Application.kt",
  "main.cpp",
  "main.c",
]);

function depthOfPath(filePath) {
  if (!filePath) return 99;
  const parts = String(filePath).replace(/\\/g, "/").split("/").filter(Boolean);
  return Math.max(0, parts.length - 1);
}

function basename(filePath, name) {
  if (name) return name;
  if (!filePath) return "";
  const parts = String(filePath).replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || "";
}

function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    fail("Usage: node ua-tour-analyze.js <input.json> <output.json>");
  }

  let raw;
  try {
    raw = fs.readFileSync(inputPath, "utf8");
  } catch (e) {
    fail("Failed to read input: " + e.message);
  }

  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    fail("Invalid JSON: " + e.message);
  }

  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];
  const layers = Array.isArray(data.layers) ? data.layers : [];

  const nodeById = new Map();
  for (const n of nodes) {
    if (n && n.id) nodeById.set(n.id, n);
  }

  const fanIn = new Map();
  const fanOut = new Map();
  for (const id of nodeById.keys()) {
    fanIn.set(id, 0);
    fanOut.set(id, 0);
  }

  const adjImportsCalls = new Map();
  const undirected = new Map();
  const bidirPairs = [];

  function addUndirected(a, b) {
    if (!undirected.has(a)) undirected.set(a, new Set());
    if (!undirected.has(b)) undirected.set(b, new Set());
    undirected.get(a).add(b);
    undirected.get(b).add(a);
  }

  const pairTypes = new Map();

  for (const e of edges) {
    if (!e || !e.source || !e.target) continue;
    if (!nodeById.has(e.source) || !nodeById.has(e.target)) continue;
    fanOut.set(e.source, (fanOut.get(e.source) || 0) + 1);
    fanIn.set(e.target, (fanIn.get(e.target) || 0) + 1);

    if (e.type === "imports" || e.type === "calls") {
      if (!adjImportsCalls.has(e.source)) adjImportsCalls.set(e.source, []);
      adjImportsCalls.get(e.source).push(e.target);
    }

    addUndirected(e.source, e.target);
    const key = e.source < e.target ? e.source + "\0" + e.target : e.target + "\0" + e.source;
    if (!pairTypes.has(key)) pairTypes.set(key, []);
    pairTypes.get(key).push(e);
  }

  // Bidirectional imports/calls
  const importCalls = edges.filter(
    (e) => e && (e.type === "imports" || e.type === "calls") && nodeById.has(e.source) && nodeById.has(e.target)
  );
  const directedIC = new Set();
  for (const e of importCalls) {
    directedIC.add(e.type + ":" + e.source + "->" + e.target);
  }
  const seenPair = new Set();
  for (const e of importCalls) {
    const revImport = "imports:" + e.target + "->" + e.source;
    const revCall = "calls:" + e.target + "->" + e.source;
    const fwdImport = "imports:" + e.source + "->" + e.target;
    const fwdCall = "calls:" + e.source + "->" + e.target;
    const hasBidir =
      (directedIC.has(fwdImport) && directedIC.has(revImport)) ||
      (directedIC.has(fwdCall) && directedIC.has(revCall));
    if (hasBidir) {
      const key = e.source < e.target ? e.source + "\0" + e.target : e.target + "\0" + e.source;
      if (!seenPair.has(key)) {
        seenPair.add(key);
        bidirPairs.push([e.source < e.target ? e.source : e.target, e.source < e.target ? e.target : e.source]);
      }
    }
  }

  const fanInRanking = [...nodeById.keys()]
    .map((id) => ({
      id,
      fanIn: fanIn.get(id) || 0,
      name: nodeById.get(id).name || basename(nodeById.get(id).filePath),
    }))
    .sort((a, b) => b.fanIn - a.fanIn)
    .slice(0, 20);

  const fanOutRanking = [...nodeById.keys()]
    .map((id) => ({
      id,
      fanOut: fanOut.get(id) || 0,
      name: nodeById.get(id).name || basename(nodeById.get(id).filePath),
    }))
    .sort((a, b) => b.fanOut - a.fanOut)
    .slice(0, 20);

  const allFanOut = [...fanOut.values()].sort((a, b) => a - b);
  const allFanIn = [...fanIn.values()].sort((a, b) => a - b);
  const fanOutP90 = allFanOut[Math.max(0, Math.floor(allFanOut.length * 0.9))] || 0;
  const fanInP25 = allFanIn[Math.max(0, Math.floor(allFanIn.length * 0.25))] || 0;

  function entryScore(n) {
    let score = 0;
    const fp = n.filePath || "";
    const name = basename(fp, n.name);
    const type = n.type || "file";
    const id = n.id;

    if (type === "document" || type === "file") {
      if (name === "README.md" && (fp === "README.md" || fp === "./README.md")) score += 5;
      else if (name.endsWith(".md") && depthOfPath(fp) === 0 && type === "document") score += 2;
    }

    if (type === "file" || id.startsWith("file:")) {
      if (CODE_ENTRY_NAMES.has(name)) score += 3;
      const d = depthOfPath(fp);
      if (d <= 1) score += 1;
      if ((fanOut.get(id) || 0) >= fanOutP90 && fanOutP90 > 0) score += 1;
      if ((fanIn.get(id) || 0) <= fanInP25) score += 1;
    }
    return score;
  }

  const entryPointCandidates = nodes
    .filter((n) => n && n.id)
    .map((n) => ({
      id: n.id,
      score: entryScore(n),
      name: n.name || basename(n.filePath),
      summary: n.summary || "",
    }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  const topCodeEntry =
    entryPointCandidates.find((c) => {
      const n = nodeById.get(c.id);
      return n && (n.type === "file" || String(c.id).startsWith("file:"));
    }) || entryPointCandidates.find((c) => String(c.id).startsWith("file:"));

  let startNode = topCodeEntry ? topCodeEntry.id : null;
  if (!startNode) {
    const fallback = nodes.find((n) => n && String(n.id).startsWith("file:"));
    startNode = fallback ? fallback.id : nodes[0] ? nodes[0].id : null;
  }

  const bfsOrder = [];
  const depthMap = {};
  const byDepth = {};
  if (startNode && nodeById.has(startNode)) {
    const visited = new Set();
    const q = [{ id: startNode, depth: 0 }];
    visited.add(startNode);
    while (q.length) {
      const { id, depth } = q.shift();
      bfsOrder.push(id);
      depthMap[id] = depth;
      const key = String(depth);
      if (!byDepth[key]) byDepth[key] = [];
      byDepth[key].push(id);
      const neighbors = adjImportsCalls.get(id) || [];
      for (const nxt of neighbors) {
        if (!visited.has(nxt) && nodeById.has(nxt)) {
          visited.add(nxt);
          q.push({ id: nxt, depth: depth + 1 });
        }
      }
    }
  }

  const documentation = [];
  const infrastructure = [];
  const dataFiles = [];
  const config = [];
  for (const n of nodes) {
    if (!n || !n.id) continue;
    const rec = { id: n.id, name: n.name || basename(n.filePath), type: n.type, summary: n.summary || "" };
    if (n.type === "document") documentation.push(rec);
    else if (n.type === "service" || n.type === "pipeline" || n.type === "resource") infrastructure.push(rec);
    else if (n.type === "table" || n.type === "schema" || n.type === "endpoint") dataFiles.push(rec);
    else if (n.type === "config") config.push(rec);
  }

  // Clusters from bidirectional pairs, expand by nodes connected to 2+ members
  const parent = new Map();
  function find(x) {
    if (!parent.has(x)) parent.set(x, x);
    if (parent.get(x) !== x) parent.set(x, find(parent.get(x)));
    return parent.get(x);
  }
  function union(a, b) {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  }
  for (const [a, b] of bidirPairs) union(a, b);

  const groups = new Map();
  for (const [a, b] of bidirPairs) {
    const r = find(a);
    if (!groups.has(r)) groups.set(r, new Set());
    groups.get(r).add(a);
    groups.get(r).add(b);
  }

  function edgeCountAmong(nodeSet) {
    const s = new Set(nodeSet);
    let count = 0;
    for (const e of edges) {
      if (e && s.has(e.source) && s.has(e.target)) count += 1;
    }
    return count;
  }

  const clusters = [];
  for (const set of groups.values()) {
    const members = new Set(set);
    let changed = true;
    while (changed) {
      changed = false;
      for (const [nid, neigh] of undirected.entries()) {
        if (members.has(nid)) continue;
        let hits = 0;
        for (const m of members) {
          if (neigh.has(m)) hits += 1;
        }
        if (hits >= 2) {
          members.add(nid);
          changed = true;
        }
      }
    }
    const arr = [...members];
    if (arr.length >= 2 && arr.length <= 5) {
      clusters.push({ nodes: arr, edgeCount: edgeCountAmong(arr) });
    } else if (arr.length > 5) {
      // keep a tightly connected subset of 2-5 by highest degree within cluster
      const deg = arr.map((id) => {
        const neigh = undirected.get(id) || new Set();
        let d = 0;
        for (const x of arr) if (neigh.has(x) && x !== id) d += 1;
        return { id, d };
      });
      deg.sort((a, b) => b.d - a.d);
      const subset = deg.slice(0, 5).map((x) => x.id);
      if (subset.length >= 2) clusters.push({ nodes: subset, edgeCount: edgeCountAmong(subset) });
    }
  }
  clusters.sort((a, b) => b.edgeCount - a.edgeCount);
  const topClusters = clusters.slice(0, 10);

  const nodeSummaryIndex = {};
  for (const n of nodes) {
    if (!n || !n.id) continue;
    nodeSummaryIndex[n.id] = {
      name: n.name || basename(n.filePath),
      type: n.type || "file",
      summary: n.summary || "",
    };
  }

  const result = {
    scriptCompleted: true,
    entryPointCandidates,
    fanInRanking,
    fanOutRanking,
    bfsTraversal: {
      startNode,
      order: bfsOrder,
      depthMap,
      byDepth,
    },
    nonCodeFiles: {
      documentation,
      infrastructure,
      data: dataFiles,
      config,
    },
    clusters: topClusters,
    layers: {
      count: layers.length,
      list: layers.map((l) => ({
        id: l.id,
        name: l.name,
        description: l.description || "",
      })),
    },
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length,
  };

  try {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  } catch (e) {
    fail("Failed to write output: " + e.message);
  }
}

try {
  main();
} catch (e) {
  fail(e && e.stack ? e.stack : e);
}
