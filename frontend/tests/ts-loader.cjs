const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const ts = require('typescript');

const frontend = path.resolve(__dirname, '..');
const packageRequire = createRequire(path.join(frontend, 'package.json'));

/** Load actual TS/TSX modules with explicit browser/network seams, no build output. */
function loader({ mocks = {}, globals = {} } = {}) {
  const cache = new Map();
  function load(relative) {
    let filename = path.isAbsolute(relative) ? relative : path.join(frontend, relative);
    if (!path.extname(filename)) {
      filename = ['.ts', '.tsx'].map(ext => filename + ext).find(fs.existsSync) ?? filename;
    }
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = { exports: {} };
    cache.set(filename, module);
    const output = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      fileName: filename,
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const localRequire = name => {
      if (Object.hasOwn(mocks, name)) return mocks[name];
      if (name.startsWith('@/')) return load(path.join(frontend, 'src', name.slice(2)));
      if (name.startsWith('.')) return load(path.resolve(path.dirname(filename), name));
      return packageRequire(name);
    };
    vm.runInNewContext(output, { module, exports: module.exports, require: localRequire,
      console, TextEncoder, URLSearchParams, ...globals }, { filename });
    return module.exports;
  }
  return load;
}

function storage() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, String(value)); },
    removeItem: key => { values.delete(key); }, clear: () => values.clear(), values };
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function plain(value) { return JSON.parse(JSON.stringify(value)); }

module.exports = { loader, storage, deferred, plain };
