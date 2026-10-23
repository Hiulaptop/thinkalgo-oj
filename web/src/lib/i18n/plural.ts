// Đánh giá biểu thức `plural=` của header Plural-Forms mà không dùng eval/new Function.
// Hỗ trợ: n, số nguyên, ( ), ! , * / %, + -, < > <= >=, == !=, &&, ||, ?:

type Tok = { t: "num"; v: number } | { t: "n" } | { t: "op"; v: string };

function tokenize(src: string): Tok[] {
  const out: Tok[] = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (/\s/.test(c)) {
      i++;
    } else if (/[0-9]/.test(c)) {
      let j = i;
      while (j < src.length && /[0-9]/.test(src[j])) j++;
      out.push({ t: "num", v: Number(src.slice(i, j)) });
      i = j;
    } else if (c === "n") {
      out.push({ t: "n" });
      i++;
    } else {
      const two = src.slice(i, i + 2);
      if (["&&", "||", "==", "!=", "<=", ">="].includes(two)) {
        out.push({ t: "op", v: two });
        i += 2;
      } else if ("()!*/%+-<>?:".includes(c)) {
        out.push({ t: "op", v: c });
        i++;
      } else {
        throw new Error(`Plural-Forms: ký tự không hỗ trợ "${c}" trong "${src}"`);
      }
    }
  }
  return out;
}

type Node = (n: number) => number;

function parse(tokens: Tok[]): Node {
  let p = 0;
  const peekOp = (...ops: string[]) => {
    const tk = tokens[p];
    return tk && tk.t === "op" && ops.includes(tk.v) ? tk.v : null;
  };
  const eat = (op: string) => {
    if (peekOp(op)) p++;
    else throw new Error(`Plural-Forms: thiếu "${op}"`);
  };

  const ternary = (): Node => {
    const cond = orExpr();
    if (peekOp("?")) {
      p++;
      const a = ternary();
      eat(":");
      const b = ternary();
      return (n) => (cond(n) ? a(n) : b(n));
    }
    return cond;
  };
  const binary = (next: () => Node, ops: string[], fn: (op: string, a: number, b: number) => number) => (): Node => {
    let left = next();
    let op: string | null;
    while ((op = peekOp(...ops))) {
      p++;
      const l = left;
      const r = next();
      const o = op;
      left = (n) => fn(o, l(n), r(n));
    }
    return left;
  };
  const unary = (): Node => {
    if (peekOp("!")) {
      p++;
      const e = unary();
      return (n) => (e(n) ? 0 : 1);
    }
    if (peekOp("(")) {
      p++;
      const e = ternary();
      eat(")");
      return e;
    }
    const tk = tokens[p++];
    if (!tk) throw new Error("Plural-Forms: biểu thức cụt");
    if (tk.t === "num") return () => tk.v;
    if (tk.t === "n") return (n) => n;
    throw new Error(`Plural-Forms: token không mong đợi "${tk.v}"`);
  };
  const mul = binary(unary, ["*", "/", "%"], (o, a, b) => (o === "*" ? a * b : o === "/" ? Math.trunc(a / b) : a % b));
  const add = binary(mul, ["+", "-"], (o, a, b) => (o === "+" ? a + b : a - b));
  const rel = binary(add, ["<", ">", "<=", ">="], (o, a, b) => Number(o === "<" ? a < b : o === ">" ? a > b : o === "<=" ? a <= b : a >= b));
  const eq = binary(rel, ["==", "!="], (o, a, b) => Number(o === "==" ? a === b : a !== b));
  const andExpr = binary(eq, ["&&"], (_o, a, b) => Number(Boolean(a) && Boolean(b)));
  const orExpr = binary(andExpr, ["||"], (_o, a, b) => Number(Boolean(a) || Boolean(b)));

  const root = ternary();
  if (p !== tokens.length) throw new Error("Plural-Forms: còn token thừa");
  return root;
}

export type PluralRule = { nplurals: number; index: (n: number) => number };

const cache = new Map<string, PluralRule>();

/** Phân tích chuỗi header, ví dụ "nplurals=1; plural=0;". */
export function parsePluralForms(header: string): PluralRule {
  const hit = cache.get(header);
  if (hit) return hit;
  const np = /nplurals\s*=\s*(\d+)/.exec(header);
  const ex = /plural\s*=\s*([^;]+)/.exec(header.replace(/nplurals\s*=\s*\d+\s*;?/, ""));
  if (!np || !ex) throw new Error(`Plural-Forms không hợp lệ: "${header}"`);
  const nplurals = Number(np[1]);
  const fn = parse(tokenize(ex[1].trim()));
  const rule: PluralRule = {
    nplurals,
    index: (n) => {
      const i = Math.trunc(fn(Math.abs(n)));
      return i >= 0 && i < nplurals ? i : 0;
    },
  };
  cache.set(header, rule);
  return rule;
}
