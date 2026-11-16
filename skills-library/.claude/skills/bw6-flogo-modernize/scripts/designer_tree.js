// Runs the Flogo designer's OWN flow loader (LinkConverter.buildActivityTree + convertTreeToItems, copied at
// run time out of the installed extension's appEditor.js) on link lists read from stdin, and prints which
// activities the designer would keep. Input: [{flow, tasks:[ids], links:[{from,to,type}]}]
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
function grab(name, next) {
  const i = src.indexOf(`e.prototype.${name}=function`);
  const j = src.indexOf(`,e.prototype.${next}=function`, i);
  if (i < 0 || j < 0) throw new Error(`cannot find ${name} in appEditor.js`);
  return src.slice(i + `e.prototype.${name}=`.length, j);
}
const buildSrc = grab("buildActivityTree", "convertTreeToDiagram");
const itemsSrc = grab("convertTreeToItems", "buildRoot");
// minimal stand-ins for the bundle's lodash (s), branch-type list (l) and branch converter
const s = { isArray: Array.isArray, isEmpty: (x) => x == null || (typeof x === "object" && Object.keys(x).length === 0),
            values: (o) => Object.values(o) };
const l = ["expression", "exprOtherwise", "label", "default", 1, 3];  // any value: only decides branch vs plain
const LinkConverter = { convertLinkToBranch: (x) => ({ id: `${x.from}->${x.to}` }) };
const buildActivityTree = eval(`(${buildSrc})`).bind(LinkConverter);
const convertTreeToItems = eval(`(${itemsSrc})`).bind(LinkConverter);

const flows = JSON.parse(fs.readFileSync(0, "utf8"));
const out = flows.map((f) => {
  const tasks = Object.fromEntries(f.tasks.map((t) => [t, { id: t, title: t, name: t }]));
  const tree = buildActivityTree(f.links, tasks, { isValid: false });
  const kept = Object.values(convertTreeToItems(tree)).filter((a) => tasks[a.id]).map((a) => a.id);
  return { flow: f.flow, kept, dropped: f.tasks.filter((t) => !kept.includes(t)) };
});
process.stdout.write(JSON.stringify(out));
