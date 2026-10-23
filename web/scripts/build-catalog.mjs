// Sinh catalog JSON cho web/ từ locale/<lang>/LC_MESSAGES/django.po.
// Chỉ giữ chuỗi mà mã trong web/src tham chiếu (t/nt/pt với đối số literal) và
// các khoá khai báo tay trong src/lib/i18n/extra-keys.json.
//   node scripts/build-catalog.mjs          ghi src/locales/<lang>.json
//   node scripts/build-catalog.mjs --check  thất bại nếu file đã commit khác kết quả sinh
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import gettextParser from "gettext-parser";

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const poRoot = path.resolve(webDir, "..", "locale");
const srcDir = path.join(webDir, "src");
const outDir = path.join(srcDir, "locales");
const cfg = JSON.parse(readFileSync(path.join(srcDir, "lib/i18n/locales.json"), "utf8"));
const CTX = "\u0004";
const checkOnly = process.argv.includes("--check");

const SKIP_DIRS = new Set([path.join(srcDir, "locales"), path.join(srcDir, "lib", "i18n")]);

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(full)) yield* walk(full);
    } else if (/\.(ts|tsx|js|jsx|mjs)$/.test(entry.name) && !/\.d\.ts$/.test(entry.name)) {
      yield full;
    }
  }
}

const ESCAPES = { n: "\n", t: "\t", r: "\r", "\\": "\\", '"': '"', "'": "'", "`": "`" };
function unescapeLiteral(raw) {
  return raw.replace(/\\(u[0-9a-fA-F]{4}|[\s\S])/g, (_, c) =>
    c[0] === "u" && c.length === 5 ? String.fromCharCode(parseInt(c.slice(1), 16)) : (ESCAPES[c] ?? c),
  );
}

const LITERAL = /(["'`])((?:\\[\s\S]|(?!\1)[^\\])*)\1/y;
const CALL = /(?<![\w.$])(nt|pt|t)\(\s*/g;

/** Thay chú thích bằng khoảng trắng (giữ nguyên số dòng) để không quét nhầm `t()` trong comment. */
function stripComments(src) {
  let out = "";
  let i = 0;
  let quote = null;
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (quote) {
      out += c;
      if (c === "\\") {
        out += src[i + 1] ?? "";
        i += 2;
        continue;
      }
      if (c === quote) quote = null;
      i++;
    } else if (c === "/" && next === "/") {
      while (i < src.length && src[i] !== "\n") {
        out += " ";
        i++;
      }
    } else if (c === "/" && next === "*") {
      const end = src.indexOf("*/", i + 2);
      const stop = end === -1 ? src.length : end + 2;
      out += src.slice(i, stop).replace(/[^\n]/g, " ");
      i = stop;
    } else {
      if (c === '"' || c === "'" || c === "`") quote = c;
      out += c;
      i++;
    }
  }
  return out;
}

function lineOf(text, index) {
  return text.slice(0, index).split("\n").length;
}

/** Trả về {keys: Set<{ctx,msgid}>, errors: string[]} */
function extractKeys() {
  const keys = new Map();
  const errors = [];
  const add = (ctx, msgid) => keys.set(`${ctx}${CTX}${msgid}`, { ctx, msgid });
  for (const file of walk(srcDir)) {
    const text = stripComments(readFileSync(file, "utf8"));
    for (const m of text.matchAll(CALL)) {
      const kind = m[1];
      let pos = m.index + m[0].length;
      const where = `${path.relative(webDir, file)}:${lineOf(text, m.index)}`;
      const readLiteral = () => {
        LITERAL.lastIndex = pos;
        const lit = LITERAL.exec(text);
        if (!lit) return null;
        if (lit[1] === "`" && lit[2].includes("${")) return null;
        pos = LITERAL.lastIndex;
        return unescapeLiteral(lit[2]);
      };
      const first = readLiteral();
      if (first === null) {
        errors.push(`${where}: ${kind}() cần đối số đầu là chuỗi literal (dùng extra-keys.json cho chuỗi động)`);
        continue;
      }
      if (kind === "pt") {
        const rest = /\s*,\s*/y;
        rest.lastIndex = pos;
        if (!rest.exec(text)) {
          errors.push(`${where}: pt() thiếu msgid`);
          continue;
        }
        pos = rest.lastIndex;
        const msgid = readLiteral();
        if (msgid === null) {
          errors.push(`${where}: pt() cần msgid là chuỗi literal`);
          continue;
        }
        add(first, msgid);
      } else {
        add("", first);
      }
    }
  }
  const extra = JSON.parse(readFileSync(path.join(srcDir, "lib/i18n/extra-keys.json"), "utf8"));
  for (const e of extra) add(e.msgctxt ?? "", e.msgid);
  return { keys, errors };
}

function build(locale, keys) {
  const poPath = path.join(poRoot, locale, "LC_MESSAGES", "django.po");
  if (!existsSync(poPath)) throw new Error(`Không thấy ${poPath}`);
  const po = gettextParser.po.parse(readFileSync(poPath));
  const plural = po.headers?.["Plural-Forms"] ?? po.headers?.["plural-forms"] ?? "nplurals=2; plural=n != 1;";
  // web.po: chuỗi riêng của giao diện Next.js, thắng django.po khi trùng (ctx, msgid).
  const webPath = path.join(poRoot, locale, "LC_MESSAGES", "web.po");
  if (existsSync(webPath)) {
    const web = gettextParser.po.parse(readFileSync(webPath));
    for (const [ctx, entries] of Object.entries(web.translations)) {
      for (const [id, entry] of Object.entries(entries)) {
        if (id === "") continue;
        po.translations[ctx] ??= {};
        po.translations[ctx][id] = entry;
      }
    }
  }
  const messages = {};
  const missing = [];
  for (const { ctx, msgid } of [...keys.values()].sort((a, b) => (a.ctx + a.msgid).localeCompare(b.ctx + b.msgid))) {
    const entry = po.translations[ctx]?.[msgid];
    const forms = entry?.msgstr ?? [];
    // msgfmt/compilemessages bỏ qua mục fuzzy, nên catalog cũng phải bỏ để giống Django.
    const fuzzy = /\bfuzzy\b/.test(entry?.comments?.flag ?? "");
    const filled = !fuzzy && forms.length > 0 && forms.every((s) => s !== "");
    if (!entry || !filled) {
      if (locale !== cfg.source) missing.push(ctx ? `[${ctx}] ${msgid}` : msgid);
      continue;
    }
    messages[ctx ? `${ctx}${CTX}${msgid}` : msgid] = entry.msgid_plural ? forms : forms[0];
  }
  return { json: { _generated: "Sinh tự động bởi scripts/build-catalog.mjs từ locale/*.po. Không sửa tay.", locale, plural, messages }, missing };
}

const { keys, errors } = extractKeys();
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

let drift = false;
for (const locale of cfg.supported) {
  const { json, missing } = build(locale, keys);
  const text = JSON.stringify(json, null, 2) + "\n";
  const file = path.join(outDir, `${locale}.json`);
  if (checkOnly) {
    const current = existsSync(file) ? readFileSync(file, "utf8") : "";
    if (current !== text) {
      console.error(`${path.relative(webDir, file)} không khớp .po/mã nguồn; chạy npm run i18n:build`);
      drift = true;
    }
  } else {
    writeFileSync(file, text);
    console.log(`${locale}: ${Object.keys(json.messages).length} khoá -> ${path.relative(webDir, file)}`);
  }
  if (missing.length) {
    console.warn(`${locale}: ${missing.length} msgid chưa có bản dịch trong .po (sẽ hiển thị tiếng Anh):`);
    for (const m of missing) console.warn(`  - ${m}`);
  }
}
if (drift) process.exit(1);
